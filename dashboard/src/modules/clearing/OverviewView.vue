<template>
	<div>
		<div v-if="loading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 6" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Active Clearing Jobs" :value="data.kpis.active_jobs" :icon="ClipboardCheck" />
				<KpiCard label="Awaiting BL" :value="data.kpis.awaiting_bl" :tone="data.kpis.awaiting_bl ? 'warn' : 'good'" :icon="FileWarning" sub="Not received / confirmed" />
				<KpiCard label="DO Pending" :value="data.kpis.do_pending" :tone="data.kpis.do_pending ? 'warn' : 'good'" :icon="FileClock" sub="Requested, not received" />
				<KpiCard label="Awaiting Port Release" :value="data.kpis.awaiting_release" :tone="data.kpis.awaiting_release ? 'danger' : 'good'" :icon="PackageOpen" sub="Discharged, not released" />
				<KpiCard label="Vessel Overdue" :value="data.kpis.vessel_overdue" :tone="data.kpis.vessel_overdue ? 'danger' : 'good'" :icon="Ship" sub="ETA passed, no ATA" />
				<KpiCard label="Uninvoiced Jobs" :value="data.kpis.uninvoiced_jobs" :tone="data.kpis.uninvoiced_jobs ? 'warn' : 'good'" :icon="Receipt" />
			</div>

			<div class="sd-card" style="margin-bottom: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main"><span class="sd-card-title-icon"><AlertCircle /></span>Attention Needed</span>
				</div>
				<table class="sd-table" v-if="data.recent_blockers.length">
					<thead><tr><th>Job</th><th>Customer</th><th>Status</th><th>Comment</th></tr></thead>
					<tbody>
						<tr v-for="row in data.recent_blockers" :key="row.name">
							<td>
								<div class="sd-cell-linkgroup">
									<button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button>
									<DeskLink doctype="Clearing Job" :name="row.name" icon-only />
								</div>
							</td>
							<td>{{ row.customer }}</td>
							<td><StatusBadge :status="row.status" /></td>
							<td>{{ row.current_comment }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="CheckCircle2" title="No open blockers logged" sub="Everything is tracking cleanly." />
			</div>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><PieChart /></span>Jobs by Status</span></div>
					<DonutChart :data="statusData" />
				</div>
				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><Building2 /></span>Top Customers (Active Jobs)</span></div>
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
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import {
	ClipboardCheck, FileWarning, FileClock, PackageOpen, Ship, Receipt,
	AlertCircle, CheckCircle2, PieChart, Building2,
} from "@lucide/vue";
import { api } from "./api";
import { statusColor } from "../../format";
import KpiCard from "../../components/KpiCard.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import DonutChart from "../../components/DonutChart.vue";
import EmptyState from "../../components/EmptyState.vue";
import DeskLink from "../../components/DeskLink.vue";

defineEmits(["open-job"]);

const loading = ref(true);
const error = ref("");
const data = ref(null);

const statusData = computed(() => {
	if (!data.value) return [];
	return data.value.jobs_by_status.map((row, idx) => ({
		label: row.status, value: row.count, color: statusColor(row.status, idx),
	}));
});

onMounted(async () => {
	try {
		data.value = await api.getOverview();
	} catch (e) {
		error.value = e.message || "Failed to load clearing overview.";
	} finally {
		loading.value = false;
	}
});
</script>
