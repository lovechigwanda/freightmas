<template>
	<div>
		<!-- Loading -->
		<div v-if="loading && !data" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 6" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="cc-overview-meta">
				<span class="sd-muted">Company-wide, all service lines &middot; updated {{ data.generated_on }}</span>
			</div>

			<!-- Headline KPI band -->
			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Active Jobs" :value="formatNumber(data.totals.active)" :icon="Boxes" sub="Across all modules" />
				<KpiCard label="Invoiced Revenue" :value="formatMoney(data.totals.revenue_invoiced)" :icon="TrendingUp" />
				<KpiCard
					label="Invoiced Margin"
					:value="formatMoney(data.totals.margin_invoiced)"
					:sub="`${data.totals.margin_pct}% margin`"
					:tone="data.totals.margin_invoiced >= 0 ? 'good' : 'danger'"
					:icon="Wallet"
				/>
				<KpiCard
					label="Needs Attention"
					:value="formatNumber(data.totals.attention)"
					:tone="data.totals.attention ? 'warn' : 'good'"
					:icon="AlertTriangle"
					sub="Open exceptions"
				/>
				<KpiCard
					label="Invoicing Overdue"
					:value="formatNumber(data.invoicing.overdue_count)"
					:tone="data.invoicing.overdue_count ? 'danger' : 'good'"
					:icon="Receipt"
					:sub="`${data.invoicing.open_count} in pipeline`"
				/>
				<KpiCard
					label="Cash (30d)"
					:value="data.cash.with_difference ? `${data.cash.with_difference} off` : 'Balanced'"
					:tone="data.cash.with_difference ? 'warn' : 'good'"
					:icon="Landmark"
					:sub="`${data.cash.reconciliations_30d} reconciliation(s)`"
				/>
			</div>

			<!-- Module scorecards -->
			<div class="cc-section-title">Service lines</div>
			<div class="cc-scorecard-grid">
				<router-link
					v-for="m in data.modules"
					:key="m.doctype"
					:to="`/${m.nav_key}`"
					class="sd-card cc-scorecard"
				>
					<div class="cc-scorecard-head">
						<span class="cc-scorecard-name">{{ m.label }}</span>
						<span v-if="m.attention" class="sd-badge sd-badge-amber">{{ m.attention }}</span>
					</div>
					<div class="cc-scorecard-active">{{ formatNumber(m.active) }} <span class="sd-muted">active</span></div>
					<div class="cc-scorecard-metrics">
						<div>
							<div class="cc-scorecard-metric-label">Invoiced Rev.</div>
							<div class="cc-scorecard-metric-value">{{ formatMoney(m.revenue_invoiced) }}</div>
						</div>
						<div>
							<div class="cc-scorecard-metric-label">Margin</div>
							<div class="cc-scorecard-metric-value" :class="m.margin_pct >= 0 ? 'pos' : 'neg'">{{ m.margin_pct }}%</div>
						</div>
					</div>
					<div v-if="m.attention" class="cc-scorecard-attn">{{ m.attention_label }}</div>
					<div v-else class="cc-scorecard-attn sd-muted">On track</div>
				</router-link>
			</div>

			<!-- Combined trend -->
			<div class="sd-card" style="margin: 16px 0;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><LineChartIcon /></span>
						Revenue, Cost &amp; Margin
					</span>
					<span class="sd-muted" style="font-size: 12px;">Invoiced &middot; last 12 months</span>
				</div>
				<Chart :option="trendOption" height="300px" />
			</div>

			<div class="sd-grid sd-grid-2">
				<!-- Invoicing pipeline -->
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main"><span class="sd-card-title-icon"><Receipt /></span>Invoicing Pipeline</span>
						<span class="sd-muted" style="font-size: 12px;">{{ formatMoney(data.invoicing.open_amount) }} open</span>
					</div>
					<table class="sd-table" v-if="data.invoicing.by_status.length">
						<thead><tr><th>Status</th><th class="sd-right">Count</th><th class="sd-right">Amount</th></tr></thead>
						<tbody>
							<tr v-for="row in data.invoicing.by_status" :key="row.status">
								<td>{{ row.status }}</td>
								<td class="sd-right">{{ formatNumber(row.count) }}</td>
								<td class="sd-right">{{ formatMoney(row.amount) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="Receipt" title="No invoice register entries" />
				</div>

				<!-- Top customers -->
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main"><span class="sd-card-title-icon"><Building2 /></span>Top Customers</span>
						<span class="sd-muted" style="font-size: 12px;">by invoiced revenue</span>
					</div>
					<ul class="sd-list">
						<li v-for="(row, idx) in data.top_customers" :key="row.customer">
							<span class="cc-list-label">
								<span class="cc-rank">{{ idx + 1 }}</span>
								<span class="cc-list-text">
									<DeskLink v-if="row.customer" doctype="Customer" :name="row.customer" plain />
									<span v-else class="sd-muted">Unassigned</span>
								</span>
							</span>
							<span class="sd-badge sd-badge-blue">{{ formatMoney(row.revenue) }}</span>
						</li>
					</ul>
					<EmptyState v-if="!data.top_customers.length" :icon="Building2" title="No invoiced revenue yet" />
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import {
	Boxes, TrendingUp, Wallet, AlertTriangle, Receipt, Landmark,
	LineChart as LineChartIcon, Building2,
} from "@lucide/vue";
import { useOverviewStore } from "../../stores/overview";
import { formatMoney, formatNumber } from "../../format";
import KpiCard from "../../components/KpiCard.vue";
import Chart from "../../components/Chart.vue";
import EmptyState from "../../components/EmptyState.vue";
import DeskLink from "../../components/DeskLink.vue";

const store = useOverviewStore();
const { data, loading, error } = storeToRefs(store);

// CVD-validated series colours (indigo / amber / teal) - see dataviz validator.
const SERIES = {
	revenue: "#4f46e5",
	cost: "#d97706",
	margin: "#0d9488",
};

const trendOption = computed(() => {
	const t = (data.value && data.value.trend) || [];
	const periods = t.map((r) => r.period);
	const mk = (key) => t.map((r) => r[key]);
	return {
		legend: { data: ["Revenue", "Cost", "Margin"], bottom: 0, icon: "roundRect", itemWidth: 12, itemHeight: 4 },
		grid: { left: 8, right: 48, top: 16, bottom: 32, containLabel: true },
		tooltip: {
			trigger: "axis",
			valueFormatter: (v) => formatMoney(v),
		},
		xAxis: {
			type: "category",
			data: periods,
			axisLine: { lineStyle: { color: "#e2e8f0" } },
			axisTick: { show: false },
			axisLabel: { color: "#64748b" },
		},
		yAxis: {
			type: "value",
			splitLine: { lineStyle: { color: "#eef0f5" } },
			axisLabel: { color: "#94a3b8", formatter: (v) => compact(v) },
		},
		series: [
			line("Revenue", mk("revenue"), SERIES.revenue),
			line("Cost", mk("cost"), SERIES.cost),
			line("Margin", mk("margin"), SERIES.margin, true),
		],
	};
});

function line(name, values, color, endLabel = false) {
	return {
		name,
		type: "line",
		smooth: true,
		symbol: "circle",
		symbolSize: 6,
		lineStyle: { width: 2, color },
		itemStyle: { color },
		emphasis: { focus: "series" },
		endLabel: endLabel
			? { show: true, color, formatter: (p) => name, fontSize: 11 }
			: { show: false },
		data: values,
	};
}

function compact(v) {
	const n = Number(v) || 0;
	if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + "M";
	if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(0) + "k";
	return String(n);
}

// Opt-in auto-refresh, paused when the Desk tab is backgrounded.
let timer = null;
function startAuto() {
	stopAuto();
	timer = setInterval(() => {
		if (document.visibilityState === "visible") store.refresh();
	}, 5 * 60 * 1000);
}
function stopAuto() {
	if (timer) clearInterval(timer);
	timer = null;
}

onMounted(() => {
	store.load();
	startAuto();
});
onBeforeUnmount(stopAuto);
</script>
