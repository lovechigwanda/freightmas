<template>
	<div>
		<div v-if="loading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 7" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Active Shipments" :value="data.kpis.active_jobs" :icon="Ship" />
				<KpiCard
					label="Overdue Arrivals"
					:value="data.kpis.overdue_arrivals"
					:tone="data.kpis.overdue_arrivals ? 'danger' : 'good'"
					:icon="ArrowDownToLine"
					sub="Import ETA passed, no ATA"
				/>
				<KpiCard
					label="Overdue Departures"
					:value="data.kpis.overdue_departures"
					:tone="data.kpis.overdue_departures ? 'danger' : 'good'"
					:icon="ArrowUpFromLine"
					sub="Export ETD passed, no ATD"
				/>
				<KpiCard
					label="Missing BL Docs"
					:value="data.kpis.missing_bl_docs"
					:tone="data.kpis.missing_bl_docs ? 'warn' : 'good'"
					:icon="FileWarning"
				/>
				<KpiCard
					label="Uninvoiced Jobs"
					:value="data.kpis.uninvoiced_jobs"
					:tone="data.kpis.uninvoiced_jobs ? 'warn' : 'good'"
					:icon="Receipt"
				/>
				<KpiCard
					label="Open DND Exposure"
					:value="formatMoney(data.kpis.dnd_exposure)"
					:sub="`${data.kpis.dnd_jobs} job(s)`"
					:tone="data.kpis.dnd_exposure ? 'warn' : 'good'"
					:icon="AlertTriangle"
				/>
				<KpiCard
					label="Overdue Container Returns"
					:value="data.kpis.overdue_container_returns"
					:tone="data.kpis.overdue_container_returns ? 'danger' : 'good'"
					:icon="PackageX"
				/>
			</div>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><PieChart /></span>
							Jobs by Status
						</span>
					</div>
					<DonutChart :data="statusData" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><TrendingUp /></span>
							Revenue &amp; Margin (last 6 months)
						</span>
						<Sparkline :values="revenueTrend" color="#4f46e5" :width="90" :height="28" />
					</div>
					<table class="sd-table">
						<thead>
							<tr><th>Month</th><th class="sd-right">Shipments</th><th class="sd-right">Revenue</th><th class="sd-right">Margin</th></tr>
						</thead>
						<tbody>
							<tr v-for="row in data.monthly_trend" :key="row.period">
								<td>{{ row.period }}</td>
								<td class="sd-right">{{ row.shipment_count }}</td>
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
							Top Customers (Active Jobs)
						</span>
					</div>
					<ul class="sd-list">
						<li v-for="(row, idx) in data.top_customers" :key="row.customer">
							<span class="cc-list-label"><span class="cc-rank">{{ idx + 1 }}</span><span class="cc-list-text">{{ row.customer }}</span></span>
							<span class="sd-badge sd-badge-blue">{{ row.job_count }}</span>
						</li>
					</ul>
					<EmptyState v-if="!data.top_customers.length" :icon="Building2" title="No active jobs" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><Route /></span>
							Top Corridors
						</span>
					</div>
					<ul class="sd-list">
						<li v-for="(row, idx) in data.top_corridors" :key="idx">
							<span class="cc-list-label"><span class="cc-rank">{{ idx + 1 }}</span><span class="cc-list-text">{{ row.port_of_loading }} &rarr; {{ row.port_of_discharge }}</span></span>
							<span class="sd-badge sd-badge-blue">{{ row.job_count }}</span>
						</li>
					</ul>
					<EmptyState v-if="!data.top_corridors.length" :icon="Route" title="No corridor data yet" />
				</div>
			</div>

			<div class="sd-card" style="margin-top: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><AlertCircle /></span>
						Recent Blockers / Exceptions
					</span>
				</div>
				<table class="sd-table" v-if="data.recent_blockers.length">
					<thead>
						<tr><th>Job</th><th>Customer</th><th>Status</th><th>Comment</th><th>Updated</th></tr>
					</thead>
					<tbody>
						<tr v-for="row in data.recent_blockers" :key="row.name">
							<td><button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button></td>
							<td>{{ row.customer }}</td>
							<td><StatusBadge :status="row.status" /></td>
							<td>{{ row.current_comment }}</td>
							<td class="sd-muted">{{ formatDate(row.last_updated_on) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="CheckCircle2" title="No open blockers logged" sub="Everything is tracking cleanly." />
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import {
	Ship, ArrowDownToLine, ArrowUpFromLine, FileWarning, Receipt, AlertTriangle, PackageX,
	PieChart, TrendingUp, Building2, Route, AlertCircle, CheckCircle2,
} from "@lucide/vue";
import { api } from "./api";
import { formatMoney, formatDate, statusColor } from "../../format";
import KpiCard from "../../components/KpiCard.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import DonutChart from "../../components/DonutChart.vue";
import Sparkline from "../../components/Sparkline.vue";
import EmptyState from "../../components/EmptyState.vue";

defineEmits(["open-job"]);

const loading = ref(true);
const error = ref("");
const data = ref(null);

const statusData = computed(() => {
	if (!data.value) return [];
	return data.value.jobs_by_status.map((row, idx) => ({
		label: row.status,
		value: row.count,
		color: statusColor(row.status, idx),
	}));
});

const revenueTrend = computed(() => {
	if (!data.value) return [];
	return data.value.monthly_trend.map((row) => Number(row.revenue) || 0);
});

onMounted(async () => {
	try {
		data.value = await api.getOverview();
	} catch (e) {
		error.value = e.message || "Failed to load overview.";
	} finally {
		loading.value = false;
	}
});
</script>
