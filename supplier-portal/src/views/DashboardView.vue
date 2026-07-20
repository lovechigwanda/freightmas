<template>
	<div>
		<div v-if="loading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 2" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="cc-overview-meta">
				<span class="sd-muted">Welcome back, {{ fullName || "there" }}.</span>
			</div>

			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Active Jobs" :value="formatNumber(data.active_jobs)" :icon="Truck" />
			</div>

			<div class="sd-card">
				<div class="sd-card-title">
					<span class="sd-card-title-main">Recent Jobs</span>
					<router-link to="/jobs" class="sd-table-link" style="font-size: 12px;">View all &rarr;</router-link>
				</div>
				<table class="sd-table" v-if="data.recent_jobs.length">
					<thead>
						<tr>
							<th>Job</th>
							<th>Route</th>
							<th>Status</th>
							<th>ETA</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="job in data.recent_jobs" :key="job.name">
							<td>
								<button class="sd-table-link" @click="openJob(job.name)">{{ job.name }}</button>
							</td>
							<td>{{ job.port_of_loading || "–" }} &rarr; {{ job.port_of_discharge || "–" }}</td>
							<td><StatusBadge :status="job.status" /></td>
							<td>{{ formatDate(job.eta) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="Truck" title="No jobs yet" sub="Jobs assigned to you will show up here." />
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { Truck } from "@lucide/vue";
import { useRouter } from "vue-router";
import { api } from "../api/dashboard";
import { formatDate, formatNumber } from "../format";
import { useSessionStore } from "../stores/session";
import KpiCard from "../components/KpiCard.vue";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";

const router = useRouter();
const session = useSessionStore();
const { fullName } = storeToRefs(session);

const data = ref(null);
const loading = ref(true);
const error = ref("");

async function load() {
	loading.value = true;
	error.value = "";
	try {
		data.value = await api.getOverview();
	} catch (e) {
		error.value = e.message || "Failed to load your dashboard.";
	} finally {
		loading.value = false;
	}
}

function openJob(name) {
	router.push(`/jobs/${encodeURIComponent("Forwarding Job")}/${encodeURIComponent(name)}`);
}

onMounted(load);
</script>
