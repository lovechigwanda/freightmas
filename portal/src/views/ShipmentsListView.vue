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
				<PhaseMultiSelect
					v-model="selectedPhases"
					:options="phaseOptions"
					@change="onPhasesChange"
				/>
				<a class="sd-table-link" :href="reportUrl" target="_blank" rel="noopener">
					<Download :size="14" style="vertical-align: -2px;" /> Download Report
				</a>
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
							<th>Reference / Cargo Count</th>
							<th>ETA / ATA</th>
							<th>Status</th>
							<th>Phase</th>
							<th>Progress</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="job in jobs" :key="job.name" :class="{ 'cc-row-overdue': job.is_overdue }">
							<td>
								<router-link class="sd-table-link" :to="`/shipments/${encodeURIComponent(job.name)}`">
									{{ job.name }}
								</router-link>
							</td>
							<td>
								{{ job.customer_reference || "–" }}<span v-if="job.cargo_count" class="sd-muted"> &middot; {{ job.cargo_count }}</span>
							</td>
							<td>
								{{ formatDate(job.eta) }}<span class="sd-muted"> &middot; {{ job.ata ? "ATA " + formatDate(job.ata) : "Pending" }}</span>
							</td>
							<td><StatusBadge :status="job.status" /></td>
							<td>{{ formatOperationalPhase(job) }}</td>
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
import { computed, ref, watch } from "vue";
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Download, SearchX } from "@lucide/vue";
import { api } from "../api/shipments";
import { formatDate } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import ProgressBar from "../components/ProgressBar.vue";
import EmptyState from "../components/EmptyState.vue";
import PhaseMultiSelect from "../components/PhaseMultiSelect.vue";
import {
	OPERATIONAL_PHASE_OPTIONS,
	formatOperationalPhase,
	phasesFromBucket,
	parsePhasesQuery,
	phasesToQuery,
} from "../operationalPhases";

const route = useRoute();
const router = useRouter();

const phaseOptions = OPERATIONAL_PHASE_OPTIONS;
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
const selectedPhases = ref([]);
const jobs = ref([]);
const totalCount = ref(0);
const loading = ref(true);
const error = ref("");
const page = ref(0);
const pageSize = 20;
let debounceTimer = null;

function applyRouteFilters() {
	const bucket = typeof route.query.bucket === "string" ? route.query.bucket : "";
	if (bucket) {
		selectedPhases.value = phasesFromBucket(bucket);
	} else {
		selectedPhases.value = parsePhasesQuery(route.query.phases);
	}
	if (selectedPhases.value.length) {
		status.value = "";
	} else if (typeof route.query.status === "string") {
		status.value = route.query.status;
	}
}

function syncStatusToRoute() {
	const query = { ...route.query };
	if (status.value) {
		query.status = status.value;
	} else {
		delete query.status;
	}
	delete query.bucket;
	delete query.phases;
	router.replace({ query });
}

function syncPhasesToRoute() {
	const query = { ...route.query };
	const phasesQuery = phasesToQuery(selectedPhases.value);
	if (phasesQuery) {
		query.phases = phasesQuery;
	} else {
		delete query.phases;
	}
	delete query.bucket;
	delete query.status;
	router.replace({ query });
}

function buildPhaseParams() {
	if (!selectedPhases.value.length) return {};
	if (selectedPhases.value.length === 1) {
		return { operational_phase: selectedPhases.value[0] };
	}
	return { operational_phases: selectedPhases.value };
}

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
			...buildPhaseParams(),
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

function onPhasesChange() {
	page.value = 0;
	if (selectedPhases.value.length) {
		status.value = "";
	}
	syncPhasesToRoute();
	load();
}

function setStatus(value) {
	if (status.value === value) return;
	status.value = value;
	page.value = 0;
	selectedPhases.value = [];
	syncStatusToRoute();
	load();
}

function changePage(delta) {
	page.value += delta;
	load();
}

const reportUrl = computed(() =>
	api.exportTrackingReportUrl({
		search: search.value,
		status: status.value,
		direction: direction.value,
		...buildPhaseParams(),
	})
);

watch(
	() => [route.query.phases, route.query.bucket, route.query.status],
	() => {
		applyRouteFilters();
		if (route.query.bucket) {
			syncPhasesToRoute();
		}
		page.value = 0;
		load();
	},
);

onMounted(() => {
	applyRouteFilters();
	if (route.query.bucket) {
		syncPhasesToRoute();
	}
	load();
});
</script>
