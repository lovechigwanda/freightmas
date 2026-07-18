<template>
	<div>
		<div class="sd-toolbar">
			<div></div>
			<a class="sd-btn sd-btn-primary" :href="exportHref" target="_blank" rel="noopener">
				<Download :size="14" stroke-width="2" /> Export to Excel
			</a>
		</div>

		<div v-if="loading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 4" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Jobs with DND/Storage Exposure" :value="data.totals.job_count" :icon="Ship" />
				<KpiCard label="Total DND Cost" :value="formatMoney(data.totals.total_dnd)" tone="warn" :icon="Clock" />
				<KpiCard label="Total Storage Cost" :value="formatMoney(data.totals.total_storage)" tone="warn" :icon="Warehouse" />
				<KpiCard label="Combined Exposure" :value="formatMoney(data.totals.total_combined)" tone="danger" :icon="AlertTriangle" />
			</div>

			<div class="sd-card" style="margin-bottom: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><ListChecks /></span>
						Jobs Accruing DND / Storage
					</span>
				</div>
				<table class="sd-table" v-if="data.jobs.length">
					<thead>
						<tr>
							<th>Job</th><th>Customer</th><th>Status</th><th>BL No.</th>
							<th class="sd-right">DND Cost</th><th class="sd-right">Storage Cost</th><th class="sd-right">Total</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="row in data.jobs" :key="row.name">
							<td><button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button></td>
							<td>{{ row.customer }}</td>
							<td><StatusBadge :status="row.status" /></td>
							<td>{{ row.bl_number || "–" }}</td>
							<td class="sd-right">{{ formatMoney(row.total_est_dnd_cost) }}</td>
							<td class="sd-right">{{ formatMoney(row.total_est_storage_cost) }}</td>
							<td class="sd-right">{{ formatMoney(row.total_est_dnd_storage_cost) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="CheckCircle2" title="No jobs currently accruing DND or storage costs" />
			</div>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><PackageX /></span>
							Containers Breaching Free Days
						</span>
					</div>
					<table class="sd-table" v-if="data.containers.length">
						<thead>
							<tr><th>Container</th><th class="sd-right">DND Days</th><th class="sd-right">Storage Days</th><th class="sd-right">Total Cost</th></tr>
						</thead>
						<tbody>
							<tr v-for="(row, idx) in data.containers" :key="idx">
								<td>{{ row.container_number }}</td>
								<td class="sd-right">{{ row.chargeable_dnd_days }}</td>
								<td class="sd-right">{{ row.chargeable_storage_days }}</td>
								<td class="sd-right">{{ formatMoney(row.total_container_cost) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="CheckCircle2" title="No containers currently over free days" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><AlertCircle /></span>
							Overdue Container Returns
						</span>
					</div>
					<table class="sd-table" v-if="data.overdue_returns.length">
						<thead>
							<tr><th>Job</th><th>Container</th><th>Customer</th><th>Return By</th></tr>
						</thead>
						<tbody>
							<tr v-for="(row, idx) in data.overdue_returns" :key="idx">
								<td><button class="sd-table-link" @click="$emit('open-job', row.job)">{{ row.job }}</button></td>
								<td>{{ row.container_number }}</td>
								<td>{{ row.customer }}</td>
								<td class="sd-muted">{{ formatDate(row.return_by_date) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="CheckCircle2" title="No overdue container returns" />
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { Download, Ship, Clock, Warehouse, AlertTriangle, ListChecks, PackageX, AlertCircle, CheckCircle2 } from "@lucide/vue";
import { api, exportUrl } from "./api";
import { formatMoney, formatDate } from "../../format";
import KpiCard from "../../components/KpiCard.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import EmptyState from "../../components/EmptyState.vue";

defineEmits(["open-job"]);

const loading = ref(true);
const error = ref("");
const data = ref(null);
const exportHref = exportUrl("dnd");

onMounted(async () => {
	try {
		data.value = await api.getDndOverview();
	} catch (e) {
		error.value = e.message || "Failed to load DND data.";
	} finally {
		loading.value = false;
	}
});
</script>
