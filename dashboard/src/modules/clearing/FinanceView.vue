<template>
	<div>
		<div v-if="loading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 4" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="sd-toolbar">
				<span class="sd-muted" style="font-size: 12px;">Recognised revenue basis &middot; submitted jobs</span>
				<a class="sd-btn sd-btn-primary" :href="exportHref" target="_blank" rel="noopener">
					<Download :size="14" stroke-width="2" /> Export to Excel
				</a>
			</div>

			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Quoted Revenue" :value="formatMoney(data.totals.quoted_revenue)" :icon="FileText" :sub="`Margin ${pct(data.totals.quoted_profit, data.totals.quoted_revenue)}%`" />
				<KpiCard label="Working Revenue" :value="formatMoney(data.totals.working_revenue)" :icon="Activity" :sub="`Margin ${pct(data.totals.working_profit, data.totals.working_revenue)}%`" />
				<KpiCard label="Invoiced Revenue" :value="formatMoney(data.totals.invoiced_revenue)" :icon="Receipt" tone="good" :sub="`Margin ${data.totals.invoiced_margin_percent}%`" />
				<KpiCard label="Invoiced Profit" :value="formatMoney(data.totals.invoiced_profit)" :icon="Wallet" :tone="data.totals.invoiced_profit >= 0 ? 'good' : 'danger'" />
			</div>

			<div class="sd-card" style="margin-bottom: 16px;">
				<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><TrendingUp /></span>Recognised Revenue &amp; Margin</span><span class="sd-muted" style="font-size: 12px;">last 12 months</span></div>
				<Chart :option="trendOption" height="280px" />
			</div>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><Wallet /></span>Job Profitability</span></div>
					<table class="sd-table" v-if="data.jobs.length">
						<thead><tr><th>Job</th><th>Customer</th><th class="sd-right">Inv. Revenue</th><th class="sd-right">Inv. Profit</th><th class="sd-right">Margin</th></tr></thead>
						<tbody>
							<tr v-for="row in data.jobs.slice(0, 30)" :key="row.name">
								<td><DeskLink doctype="Clearing Job" :name="row.name" plain /></td>
								<td>{{ row.customer }}</td>
								<td class="sd-right">{{ formatMoney(row.invoiced_revenue) }}</td>
								<td class="sd-right">{{ formatMoney(row.invoiced_profit) }}</td>
								<td class="sd-right">{{ row.invoiced_margin_percent }}%</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="Wallet" title="No submitted clearing jobs" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><Receipt /></span>Outstanding Sales Invoices</span></div>
					<table class="sd-table" v-if="data.outstanding_sales_invoices.length">
						<thead><tr><th>Invoice</th><th>Customer</th><th>Due</th><th class="sd-right">Balance</th></tr></thead>
						<tbody>
							<tr v-for="inv in data.outstanding_sales_invoices" :key="inv.name">
								<td><DeskLink doctype="Sales Invoice" :name="inv.name" plain /></td>
								<td>{{ inv.customer }}</td>
								<td>{{ formatDate(inv.due_date) }}</td>
								<td class="sd-right">{{ formatMoney(inv.outstanding_amount) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="CheckCircle2" title="Nothing outstanding" />
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { Download, FileText, Activity, Receipt, Wallet, TrendingUp, CheckCircle2 } from "@lucide/vue";
import { api, exportUrl } from "./api";
import { formatMoney, formatDate } from "../../format";
import KpiCard from "../../components/KpiCard.vue";
import Chart from "../../components/Chart.vue";
import EmptyState from "../../components/EmptyState.vue";
import DeskLink from "../../components/DeskLink.vue";

const loading = ref(true);
const error = ref("");
const data = ref(null);

function pct(profit, revenue) {
	return revenue ? Math.round((profit / revenue) * 100) : 0;
}

const trendOption = computed(() => {
	const t = (data.value && data.value.monthly_trend) || [];
	return {
		legend: { data: ["Revenue", "Margin"], bottom: 0, icon: "roundRect", itemWidth: 12, itemHeight: 4 },
		grid: { left: 8, right: 16, top: 16, bottom: 32, containLabel: true },
		tooltip: { trigger: "axis", valueFormatter: (v) => formatMoney(v) },
		xAxis: { type: "category", data: t.map((r) => r.period), axisTick: { show: false }, axisLabel: { color: "#64748b" }, axisLine: { lineStyle: { color: "#e2e8f0" } } },
		yAxis: { type: "value", splitLine: { lineStyle: { color: "#eef0f5" } }, axisLabel: { color: "#94a3b8", formatter: compact } },
		series: [
			{ name: "Revenue", type: "bar", barWidth: "40%", itemStyle: { color: "#4f46e5", borderRadius: [4, 4, 0, 0] }, data: t.map((r) => r.revenue) },
			{ name: "Margin", type: "line", smooth: true, symbol: "circle", symbolSize: 6, lineStyle: { width: 2, color: "#0d9488" }, itemStyle: { color: "#0d9488" }, data: t.map((r) => r.margin) },
		],
	};
});

function compact(v) {
	const n = Number(v) || 0;
	if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + "M";
	if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(0) + "k";
	return String(n);
}

const exportHref = computed(() => exportUrl("finance", {}));

onMounted(async () => {
	try {
		data.value = await api.getFinanceSummary({});
	} catch (e) {
		error.value = e.message || "Failed to load clearing finance.";
	} finally {
		loading.value = false;
	}
});
</script>
