<template>
	<div>
		<div class="sd-toolbar">
			<nav class="sd-tabs" style="margin-bottom: 0;">
				<button
					v-for="jt in jobTypes"
					:key="jt"
					class="sd-tab"
					:class="{ active: jobDoctype === jt }"
					@click="setJobDoctype(jt)"
				>
					{{ jt }}
				</button>
			</nav>

			<div class="sd-filters" style="margin-bottom: 0;">
				<select v-model="status" @change="onFilterChange">
					<option value="">All Statuses</option>
					<option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
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
							<th>Route</th>
							<th>Status</th>
							<th>ETA / ATA</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="job in jobs" :key="job.name">
							<td>
								<router-link
									class="sd-table-link"
									:to="`/jobs/${encodeURIComponent(jobDoctype)}/${encodeURIComponent(job.name)}`"
								>
									{{ job.name }}
								</router-link>
							</td>
							<td>{{ job.port_of_loading || job.origin || "–" }} &rarr; {{ job.port_of_discharge || job.destination || "–" }}</td>
							<td><StatusBadge :status="job.status" /></td>
							<td>
								{{ formatDate(job.eta) }}<span class="sd-muted" v-if="job.eta"> &middot; {{ job.ata ? "ATA " + formatDate(job.ata) : "Pending" }}</span>
							</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="SearchX" title="No jobs match these filters" sub="Try a different job type or status." />

				<div v-if="jobs.length" style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px;">
					<span class="sd-muted" style="font-size: 12px;">{{ totalCount }} job(s)</span>
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
import { ref, onMounted } from "vue";
import { SearchX } from "@lucide/vue";
import { api } from "../api/jobs";
import { formatDate } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";

const statusOptions = ["In Progress", "Completed", "Closed", "Cancelled"];

const jobTypes = ref(["Forwarding Job"]);
const jobDoctype = ref("Forwarding Job");
const status = ref("");
const jobs = ref([]);
const totalCount = ref(0);
const loading = ref(true);
const error = ref("");
const page = ref(0);
const pageSize = 20;

async function load() {
	loading.value = true;
	error.value = "";
	try {
		const res = await api.getJobs({
			job_doctype: jobDoctype.value,
			status: status.value,
			limit_start: page.value * pageSize,
			limit_page_length: pageSize,
		});
		jobs.value = res.jobs;
		totalCount.value = res.total_count;
	} catch (e) {
		error.value = e.message || "Failed to load jobs.";
	} finally {
		loading.value = false;
	}
}

function onFilterChange() {
	page.value = 0;
	load();
}

function setJobDoctype(jt) {
	if (jobDoctype.value === jt) return;
	jobDoctype.value = jt;
	page.value = 0;
	load();
}

function changePage(delta) {
	page.value += delta;
	load();
}

onMounted(async () => {
	try {
		const types = await api.getJobTypes();
		if (types && types.length) jobTypes.value = types;
	} catch (e) {
		// keep the default single-type tab if this call fails
	}
	load();
});
</script>
