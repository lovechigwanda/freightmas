<template>
	<div>
		<div class="cc-banner">
			<Info :size="16" stroke-width="2" />
			<span><strong>Company Overview</strong> &mdash; currently sourced from the Forwarding module (the only module
			wired up so far). As Clearing, Trucking, Warehouse etc. are added, this page will aggregate across
			all of them.</span>
		</div>

		<div v-if="loading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 6" :key="i"></div>
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
			</div>

			<div class="sd-card" style="margin-bottom: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><AlertCircle /></span>
						Attention Needed
					</span>
				</div>
				<table class="sd-table" v-if="data.recent_blockers.length">
					<thead>
						<tr><th>Job</th><th>Customer</th><th>Status</th><th>Comment</th><th>Module</th></tr>
					</thead>
					<tbody>
						<tr v-for="row in data.recent_blockers" :key="row.name">
							<td><button class="sd-table-link" @click="openJob(row.name)">{{ row.name }}</button></td>
							<td>{{ row.customer }}</td>
							<td><StatusBadge :status="row.status" /></td>
							<td>{{ row.current_comment }}</td>
							<td><span class="sd-badge sd-badge-blue">Forwarding</span></td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="CheckCircle2" title="No open blockers logged" sub="Everything is tracking cleanly." />
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
			</div>
		</template>

		<!-- JobDetailModal is Forwarding-specific for now (only job type wired up).
		     Once other modules are added, this should dispatch to a generic
		     detail component based on the row's module/doctype. -->
		<JobDetailModal v-if="selectedJob" :job-name="selectedJob" @close="selectedJob = null" />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import {
	Info, Ship, ArrowDownToLine, ArrowUpFromLine, FileWarning, Receipt, AlertTriangle,
	AlertCircle, CheckCircle2, PieChart, Building2,
} from "@lucide/vue";
import { api as forwardingApi } from "../forwarding/api";
import JobDetailModal from "../forwarding/JobDetailModal.vue";
import { formatMoney, statusColor } from "../../format";
import KpiCard from "../../components/KpiCard.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import DonutChart from "../../components/DonutChart.vue";
import EmptyState from "../../components/EmptyState.vue";

const loading = ref(true);
const error = ref("");
const data = ref(null);
const selectedJob = ref(null);

const statusData = computed(() => {
	if (!data.value) return [];
	return data.value.jobs_by_status.map((row, idx) => ({
		label: row.status,
		value: row.count,
		color: statusColor(row.status, idx),
	}));
});

function openJob(jobName) {
	selectedJob.value = jobName;
}

onMounted(async () => {
	try {
		// Sourced directly from the Forwarding module until other modules exist.
		data.value = await forwardingApi.getOverview();
	} catch (e) {
		error.value = e.message || "Failed to load overview.";
	} finally {
		loading.value = false;
	}
});
</script>
