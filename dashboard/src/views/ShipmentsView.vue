<template>
	<div>
		<div class="sd-toolbar">
			<div class="sd-filters" style="margin-bottom: 0;">
				<input v-model="search" type="text" placeholder="Search job, BL, reference, vessel..." @input="onFilterChange" />
				<select v-model="status" @change="onFilterChange">
					<option value="">All Statuses</option>
					<option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
				</select>
				<select v-model="direction" @change="onFilterChange">
					<option value="">All Directions</option>
					<option v-for="d in directions" :key="d" :value="d">{{ d }}</option>
				</select>
			</div>
			<a class="sd-btn sd-btn-primary" :href="exportHref" target="_blank" rel="noopener">Export to Excel</a>
		</div>

		<div class="sd-card">
			<div v-if="loading" class="sd-state">Loading shipments...</div>
			<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>
			<template v-else>
				<table class="sd-table">
					<thead>
						<tr>
							<th>Job</th>
							<th>Customer</th>
							<th>Route</th>
							<th>Vessel / BL</th>
							<th>ETA / ATA</th>
							<th>Status</th>
							<th>Progress</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="job in jobs" :key="job.name" :style="job.is_overdue ? 'background:#fdeaea' : ''">
							<td><button class="sd-table-link" @click="$emit('open-job', job.name)">{{ job.name }}</button></td>
							<td>{{ job.customer }}</td>
							<td>{{ job.port_of_loading || "\u2013" }} &rarr; {{ job.port_of_discharge || "\u2013" }}</td>
							<td>
								<div>{{ job.vessel_flight_no || "\u2013" }}</div>
								<div class="sd-muted" style="font-size: 11px;">{{ job.bl_number || "\u2013" }}</div>
							</td>
							<td>
								<div>{{ formatDate(job.eta) }}</div>
								<div class="sd-muted" style="font-size: 11px;">{{ job.ata ? formatDate(job.ata) : "Pending" }}</div>
							</td>
							<td><StatusBadge :status="job.status" /></td>
							<td><ProgressBar :percent="job.milestone_percent" /></td>
						</tr>
						<tr v-if="!jobs.length">
							<td colspan="7" class="sd-muted" style="text-align: center; padding: 24px;">No shipments match these filters.</td>
						</tr>
					</tbody>
				</table>

				<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
					<span class="sd-muted" style="font-size: 12px;">{{ totalCount }} shipment(s)</span>
					<div style="display: flex; gap: 8px;">
						<button class="sd-table-link" :disabled="page === 0" @click="changePage(-1)">&larr; Prev</button>
						<button class="sd-table-link" :disabled="(page + 1) * pageSize >= totalCount" @click="changePage(1)">Next &rarr;</button>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { api, exportUrl } from "../api";
import { formatDate } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import ProgressBar from "../components/ProgressBar.vue";

defineEmits(["open-job"]);

const statuses = ["Draft", "In Progress", "Delivered", "Completed", "Closed", "Cancelled"];
const directions = ["Import", "Export", "Local", "Transit"];

const search = ref("");
const status = ref("");
const direction = ref("");
const jobs = ref([]);
const totalCount = ref(0);
const loading = ref(true);
const error = ref("");
const page = ref(0);
const pageSize = 20;
let debounceTimer = null;

async function load() {
	loading.value = true;
	error.value = "";
	try {
		const res = await api.getJobs({
			search: search.value,
			status: status.value,
			direction: direction.value,
			limit_start: page.value * pageSize,
			limit_page_length: pageSize,
		});
		jobs.value = res.jobs;
		totalCount.value = res.total_count;
	} catch (e) {
		error.value = e.message || "Failed to load shipments.";
	} finally {
		loading.value = false;
	}
}

function onFilterChange() {
	page.value = 0;
	clearTimeout(debounceTimer);
	debounceTimer = setTimeout(load, 300);
}

const exportHref = computed(() =>
	exportUrl("shipments", { search: search.value, status: status.value, direction: direction.value })
);

function changePage(delta) {
	page.value += delta;
	load();
}

onMounted(load);
</script>
