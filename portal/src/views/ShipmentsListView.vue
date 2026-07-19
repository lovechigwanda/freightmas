<template>
	<div>
		<div class="sd-toolbar">
			<nav class="sd-tabs" style="margin-bottom: 0;">
				<button
					v-for="tab in statusTabs"
					:key="tab.value"
					class="sd-tab"
					:class="{ active: status === tab.value }"
					@click="setStatus(tab.value)"
				>
					{{ tab.label }}
				</button>
			</nav>

			<div class="sd-filters" style="margin-bottom: 0;">
				<input v-model="search" type="text" placeholder="Search job, BL, reference..." @input="onFilterChange" />
				<select v-model="direction" @change="onFilterChange">
					<option value="">All Directions</option>
					<option v-for="d in directions" :key="d" :value="d">{{ d }}</option>
				</select>
			</div>
		</div>

		<div class="sd-card">
			<div v-if="loading">
				<div class="cc-row-skeleton cc-skeleton" v-for="i in 8" :key="i"></div>
			</div>
			<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>
			<template v-else>
				<table class="sd-table" v-if="jobs.length">
					<thead>
						<tr>
							<th>Job</th>
							<th>BL / Cargo Count</th>
							<th>ETA / ATA</th>
							<th>Status</th>
							<th>Progress</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="job in jobs" :key="job.name" :class="{ 'cc-row-overdue': job.is_overdue }">
							<td>
								<router-link class="sd-table-link" :to="`/shipments/${encodeURIComponent(job.name)}`">
									{{ job.name }}
								</router-link>
								<div class="sd-muted" style="font-size: 12px;">{{ job.customer_reference || "–" }}</div>
							</td>
							<td>
								{{ job.bl_number || "–" }}<span v-if="job.cargo_count" class="sd-muted"> &middot; {{ job.cargo_count }}</span>
							</td>
							<td>
								{{ formatDate(job.eta) }}<span class="sd-muted"> &middot; {{ job.ata ? "ATA " + formatDate(job.ata) : "Pending" }}</span>
							</td>
							<td><StatusBadge :status="job.status" /></td>
							<td><ProgressBar :percent="job.milestone_percent" /></td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="SearchX" title="No shipments match these filters" sub="Try clearing the search or filters above." />

				<div v-if="jobs.length" style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px;">
					<span class="sd-muted" style="font-size: 12px;">{{ totalCount }} shipment(s)</span>
					<div style="display: flex; gap: 8px; align-items: center;">
						<button class="sd-table-link" :disabled="page === 0" @click="changePage(-1)">&larr; Prev</button>
						<button class="sd-table-link" :disabled="(page + 1) * pageSize >= totalCount" @click="changePage(1)">Next &rarr;</button>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";
import { onMounted } from "vue";
import { SearchX } from "@lucide/vue";
import { api } from "../api/shipments";
import { formatDate } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import ProgressBar from "../components/ProgressBar.vue";
import EmptyState from "../components/EmptyState.vue";

const statusTabs = [
	{ value: "", label: "All" },
	{ value: "In Progress", label: "In Progress" },
	{ value: "Delivered", label: "Delivered" },
	{ value: "Completed", label: "Completed" },
	{ value: "Closed", label: "Closed" },
];
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

function setStatus(value) {
	if (status.value === value) return;
	status.value = value;
	page.value = 0;
	load();
}

function changePage(delta) {
	page.value += delta;
	load();
}

onMounted(load);
</script>
