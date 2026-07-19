<template>
	<div>
		<div class="sd-toolbar">
			<div></div>
			<a class="sd-btn sd-btn-primary" :href="exportHref" target="_blank" rel="noopener">
				<Download :size="14" stroke-width="2" /> Export to Excel
			</a>
		</div>

		<div v-if="loading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 6" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Quoted Revenue" :value="formatMoney(data.totals.quoted_revenue)" :icon="FileText" />
				<KpiCard label="Working Revenue" :value="formatMoney(data.totals.working_revenue)" :icon="Wallet" />
				<KpiCard label="Invoiced Revenue" :value="formatMoney(data.totals.invoiced_revenue)" :icon="Receipt" />
				<KpiCard
					label="Invoiced Margin"
					:value="formatMoney(data.totals.invoiced_profit)"
					:sub="`${data.totals.invoiced_margin_percent.toFixed(1)}%`"
					:icon="TrendingUp"
					tone="good"
				/>
				<KpiCard
					label="Loss-Making Jobs"
					:value="data.loss_making_jobs.length"
					:tone="data.loss_making_jobs.length ? 'danger' : 'good'"
					:icon="TrendingDown"
				/>
				<KpiCard
					label="Margin-at-Risk Jobs"
					:value="data.margin_at_risk_jobs.length"
					:tone="data.margin_at_risk_jobs.length ? 'warn' : 'good'"
					:icon="AlertTriangle"
				/>
			</div>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><TrendingUp /></span>
							Monthly Revenue &amp; Margin Trend
						</span>
					</div>
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
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><Building2 /></span>
							Top Customers by Invoiced Revenue
						</span>
					</div>
					<ul class="sd-list" v-if="data.top_customers_by_revenue.length">
						<li v-for="(row, idx) in data.top_customers_by_revenue" :key="row.customer">
							<span class="cc-list-label"><span class="cc-rank">{{ idx + 1 }}</span><span class="cc-list-text">{{ row.customer }}</span></span>
							<span>{{ formatMoney(row.revenue) }}</span>
						</li>
					</ul>
					<EmptyState v-else :icon="Building2" title="No invoiced revenue yet" />
				</div>

			</div>

			<div class="sd-card" style="margin-top: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><TrendingDown /></span>
						Loss-Making Closed Jobs
					</span>
				</div>
				<table class="sd-table" v-if="data.loss_making_jobs.length">
					<thead>
						<tr><th>Job</th><th>Customer</th><th>Completed</th><th class="sd-right">Invoiced Profit</th></tr>
					</thead>
					<tbody>
						<tr v-for="row in data.loss_making_jobs" :key="row.name" class="cc-row-overdue">
							<td><button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button></td>
							<td>{{ row.customer }}</td>
							<td class="sd-muted">{{ formatDate(row.completed_on) }}</td>
							<td class="sd-right">{{ formatMoney(row.invoiced_profit) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="CheckCircle2" title="No closed jobs realized a loss" />
			</div>

			<div class="sd-card" style="margin-top: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><BarChart3 /></span>
						Quoted vs Actual Margin (Closed Jobs)
					</span>
				</div>
				<table class="sd-table" v-if="data.margin_variance_jobs.length">
					<thead>
						<tr>
							<th>Job</th><th>Customer</th>
							<th class="sd-right">Quoted Margin %</th><th class="sd-right">Invoiced Margin %</th>
							<th class="sd-right">Margin Gap (pts)</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in data.margin_variance_jobs"
							:key="row.name"
							:class="{ 'cc-row-overdue': row.breaches_threshold }"
						>
							<td><button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button></td>
							<td>{{ row.customer }}</td>
							<td class="sd-right">{{ (row.quoted_margin_percent || 0).toFixed(1) }}%</td>
							<td class="sd-right">{{ row.invoiced_margin_percent.toFixed(1) }}%</td>
							<td class="sd-right">{{ row.margin_percent_gap.toFixed(1) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="BarChart3" title="No closed jobs to compare yet" />
			</div>

			<div class="sd-grid sd-grid-2" style="margin-top: 16px;">
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><AlertTriangle /></span>
							Margin at Risk (Open Jobs)
						</span>
					</div>
					<table class="sd-table" v-if="data.margin_at_risk_jobs.length">
						<thead>
							<tr>
								<th>Job</th><th>Customer</th>
								<th class="sd-right">Quoted %</th><th class="sd-right">Current %</th><th class="sd-right">Gap</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in data.margin_at_risk_jobs" :key="row.name">
								<td><button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button></td>
								<td>{{ row.customer }}</td>
								<td class="sd-right">{{ (row.quoted_margin_percent || 0).toFixed(1) }}%</td>
								<td class="sd-right">{{ (row.profit_margin_percent || 0).toFixed(1) }}%</td>
								<td class="sd-right">{{ row.margin_gap.toFixed(1) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="CheckCircle2" title="No open jobs trailing their quoted margin" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><Building2 /></span>
							Loss-Making Customers
						</span>
					</div>
					<ul class="sd-list" v-if="data.loss_making_customers.length">
						<li v-for="(row, idx) in data.loss_making_customers" :key="row.customer">
							<span class="cc-list-label"><span class="cc-rank">{{ idx + 1 }}</span><span class="cc-list-text">{{ row.customer }}</span></span>
							<span>{{ row.job_count }} job(s) &middot; {{ formatMoney(row.invoiced_profit) }}</span>
						</li>
					</ul>
					<EmptyState v-else :icon="CheckCircle2" title="No customers with a net loss" />
				</div>
			</div>

			<div class="sd-card" style="margin-top: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><FileText /></span>
						Overdue Invoice Aging
					</span>
				</div>
				<table class="sd-table">
					<thead>
						<tr><th></th><th class="sd-right">0-30 days</th><th class="sd-right">31-60 days</th><th class="sd-right">61-90 days</th><th class="sd-right">90+ days</th></tr>
					</thead>
					<tbody>
						<tr>
							<td>Sales (owed to us)</td>
							<td class="sd-right" v-for="b in data.aging_summary.sales" :key="b.bucket">{{ b.count }} &middot; {{ formatMoney(b.value) }}</td>
						</tr>
						<tr>
							<td>Purchase (owed by us)</td>
							<td class="sd-right" v-for="b in data.aging_summary.purchase" :key="b.bucket">{{ b.count }} &middot; {{ formatMoney(b.value) }}</td>
						</tr>
					</tbody>
				</table>
			</div>

			<div class="sd-grid sd-grid-2" style="margin-top: 16px;">
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><FileText /></span>
							Overdue Sales Invoices
						</span>
					</div>
					<table class="sd-table" v-if="data.overdue_sales_invoices.length">
						<thead>
							<tr><th>No.</th><th>Customer</th><th>Due</th><th class="sd-right">Days Overdue</th><th class="sd-right">Balance</th></tr>
						</thead>
						<tbody>
							<tr
								v-for="inv in data.overdue_sales_invoices"
								:key="inv.name"
								:class="{ 'cc-row-overdue': inv.days_overdue > 60 }"
							>
								<td>{{ inv.name }}</td>
								<td>{{ inv.party }}</td>
								<td>{{ formatDate(inv.due_date) }}</td>
								<td class="sd-right">{{ inv.days_overdue }}</td>
								<td class="sd-right">{{ formatMoney(inv.outstanding_amount) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="CheckCircle2" title="No overdue sales invoices" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><FileText /></span>
							Overdue Purchase Invoices
						</span>
					</div>
					<table class="sd-table" v-if="data.overdue_purchase_invoices.length">
						<thead>
							<tr><th>No.</th><th>Supplier</th><th>Due</th><th class="sd-right">Days Overdue</th><th class="sd-right">Balance</th></tr>
						</thead>
						<tbody>
							<tr
								v-for="inv in data.overdue_purchase_invoices"
								:key="inv.name"
								:class="{ 'cc-row-overdue': inv.days_overdue > 60 }"
							>
								<td>{{ inv.name }}</td>
								<td>{{ inv.party }}</td>
								<td>{{ formatDate(inv.due_date) }}</td>
								<td class="sd-right">{{ inv.days_overdue }}</td>
								<td class="sd-right">{{ formatMoney(inv.outstanding_amount) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="CheckCircle2" title="No overdue purchase invoices" />
				</div>
			</div>

			<div class="sd-card" style="margin-top: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><BarChart3 /></span>
						Job Profitability (Quoted vs Working vs Invoiced)
					</span>
				</div>
				<table class="sd-table" v-if="data.jobs.length">
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
					</tbody>
				</table>
				<EmptyState v-else :icon="BarChart3" title="No submitted jobs in this range" />
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { Download, FileText, Wallet, Receipt, TrendingUp, TrendingDown, AlertTriangle, Building2, CheckCircle2, BarChart3 } from "@lucide/vue";
import { api, exportUrl } from "./api";
import { formatMoney, formatDate } from "../../format";
import KpiCard from "../../components/KpiCard.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import EmptyState from "../../components/EmptyState.vue";

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
