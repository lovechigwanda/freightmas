<template>
	<div>
		<div class="sd-toolbar">
			<div></div>
			<a class="sd-btn sd-btn-primary" :href="exportHref" target="_blank" rel="noopener">Export to Excel</a>
		</div>

		<div v-if="loading" class="sd-state">Loading finance data...</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Quoted Revenue" :value="formatMoney(data.totals.quoted_revenue)" />
				<KpiCard label="Working Revenue" :value="formatMoney(data.totals.working_revenue)" />
				<KpiCard label="Invoiced Revenue" :value="formatMoney(data.totals.invoiced_revenue)" />
				<KpiCard
					label="Invoiced Margin"
					:value="formatMoney(data.totals.invoiced_profit)"
					:sub="`${data.totals.invoiced_margin_percent.toFixed(1)}%`"
				/>
			</div>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title">Monthly Revenue &amp; Margin Trend</div>
					<table class="sd-table">
						<thead>
							<tr><th>Month</th><th class="sd-right">Revenue</th><th class="sd-right">Margin</th></tr>
						</thead>
						<tbody>
							<tr v-for="row in data.monthly_trend" :key="row.period">
								<td>{{ row.period }}</td>
								<td class="sd-right">{{ formatMoney(row.revenue) }}</td>
								<td class="sd-right">{{ formatMoney(row.margin) }}</td>
							</tr>
						</tbody>
					</table>
				</div>

				<div class="sd-card">
					<div class="sd-card-title">Top Customers by Invoiced Revenue</div>
					<ul class="sd-list">
						<li v-for="row in data.top_customers_by_revenue" :key="row.customer">
							<span>{{ row.customer }}</span>
							<span>{{ formatMoney(row.revenue) }}</span>
						</li>
						<li v-if="!data.top_customers_by_revenue.length" class="sd-muted">No invoiced revenue yet.</li>
					</ul>
				</div>

				<div class="sd-card">
					<div class="sd-card-title">Outstanding Sales Invoices</div>
					<table class="sd-table" v-if="data.outstanding_sales_invoices.length">
						<thead>
							<tr><th>No.</th><th>Customer</th><th>Due</th><th class="sd-right">Balance</th></tr>
						</thead>
						<tbody>
							<tr v-for="inv in data.outstanding_sales_invoices" :key="inv.name">
								<td>{{ inv.name }}</td>
								<td>{{ inv.customer }}</td>
								<td>{{ formatDate(inv.due_date) }}</td>
								<td class="sd-right">{{ formatMoney(inv.outstanding_amount) }}</td>
							</tr>
						</tbody>
					</table>
					<div v-else class="sd-muted" style="font-size: 13px;">No outstanding sales invoices.</div>
				</div>

				<div class="sd-card">
					<div class="sd-card-title">Outstanding Purchase Invoices</div>
					<table class="sd-table" v-if="data.outstanding_purchase_invoices.length">
						<thead>
							<tr><th>No.</th><th>Supplier</th><th>Due</th><th class="sd-right">Balance</th></tr>
						</thead>
						<tbody>
							<tr v-for="inv in data.outstanding_purchase_invoices" :key="inv.name">
								<td>{{ inv.name }}</td>
								<td>{{ inv.supplier }}</td>
								<td>{{ formatDate(inv.due_date) }}</td>
								<td class="sd-right">{{ formatMoney(inv.outstanding_amount) }}</td>
							</tr>
						</tbody>
					</table>
					<div v-else class="sd-muted" style="font-size: 13px;">No outstanding purchase invoices.</div>
				</div>
			</div>

			<div class="sd-card" style="margin-top: 16px;">
				<div class="sd-card-title">Job Profitability (Quoted vs Working vs Invoiced)</div>
				<table class="sd-table">
					<thead>
						<tr>
							<th>Job</th><th>Customer</th><th>Status</th>
							<th class="sd-right">Quoted Rev</th><th class="sd-right">Working Rev</th>
							<th class="sd-right">Invoiced Rev</th><th class="sd-right">Invoiced Margin %</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="row in data.jobs" :key="row.name">
							<td><button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button></td>
							<td>{{ row.customer }}</td>
							<td><StatusBadge :status="row.status" /></td>
							<td class="sd-right">{{ formatMoney(row.quoted_revenue) }}</td>
							<td class="sd-right">{{ formatMoney(row.working_revenue) }}</td>
							<td class="sd-right">{{ formatMoney(row.invoiced_revenue) }}</td>
							<td class="sd-right">{{ row.invoiced_margin_percent.toFixed(1) }}%</td>
						</tr>
						<tr v-if="!data.jobs.length">
							<td colspan="7" class="sd-muted" style="text-align: center; padding: 24px;">No submitted jobs in this range.</td>
						</tr>
					</tbody>
				</table>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { api, exportUrl } from "../api";
import { formatMoney, formatDate } from "../format";
import KpiCard from "../components/KpiCard.vue";
import StatusBadge from "../components/StatusBadge.vue";

defineEmits(["open-job"]);

const loading = ref(true);
const error = ref("");
const data = ref(null);
const exportHref = exportUrl("finance");

onMounted(async () => {
	try {
		data.value = await api.getFinanceSummary({});
	} catch (e) {
		error.value = e.message || "Failed to load finance data.";
	} finally {
		loading.value = false;
	}
});
</script>
