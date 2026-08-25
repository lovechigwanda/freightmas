<template>
	<div>
		<div v-if="loading" class="sd-phase-pipeline">
			<div class="sd-card sd-phase-pipeline-skeleton cc-skeleton" v-for="i in 7" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="cc-overview-meta">
				<span class="sd-muted">Welcome back, {{ fullName || "there" }}.</span>
			</div>

			<div style="margin-bottom: 18px;">
				<h3 class="sd-pipeline-section-title">Shipment Pipeline</h3>
				<div class="sd-phase-pipeline">
					<PhasePipelineCard
						v-for="(bucket, idx) in data.phase_pipeline"
						:key="bucket.key"
						:label="bucket.label"
						:title="bucket.title || bucket.label"
						:count="bucket.count"
						:icon="pipelineMeta(bucket.key).icon"
						:tone="pipelineMeta(bucket.key).tone"
						:show-connector="idx < data.phase_pipeline.length - 1"
						@click="navigateToBucket(bucket.key)"
					/>
				</div>
			</div>

			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard
					label="Outstanding"
					:value="formatMoney(data.outstanding_amount)"
					:tone="data.outstanding_amount ? 'warn' : 'good'"
					:icon="Wallet"
				/>
				<KpiCard
					label="Overdue Invoices"
					:value="formatMoney(data.overdue_amount)"
					:tone="data.overdue_amount ? 'danger' : 'good'"
					:icon="Receipt"
				/>
			</div>

			<div class="sd-card">
				<div class="sd-card-title">
					<span class="sd-card-title-main">Recent Shipments</span>
					<router-link to="/shipments" class="sd-table-link" style="font-size: 12px;">View all &rarr;</router-link>
				</div>
				<table class="sd-table" v-if="data.recent_jobs.length">
					<thead>
						<tr>
							<th>Job / Reference</th>
							<th>Route</th>
							<th>Status</th>
							<th>ETA</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="job in data.recent_jobs" :key="job.name">
							<td>
								<button class="sd-table-link" @click="openJob(job.name)">{{ job.name }}</button>
								<div class="sd-muted" style="font-size: 12px;">{{ job.customer_reference || "–" }}</div>
							</td>
							<td>{{ job.port_of_loading || "–" }} &rarr; {{ job.destination || job.port_of_discharge || "–" }}</td>
							<td><StatusBadge :status="job.status" /></td>
							<td>{{ formatDate(job.eta) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="Ship" title="No shipments yet" sub="Your active shipments will show up here." />
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { Ship, Wallet, Receipt, MapPin } from "@lucide/vue";
import { api } from "../api/dashboard";
import { formatDate, formatMoney } from "../format";
import { useSessionStore } from "../stores/session";
import {
	OVERVIEW_PIPELINE_META,
	phasesFromBucket,
	phasesToQuery,
} from "../operationalPhases";
import KpiCard from "../components/KpiCard.vue";
import PhasePipelineCard from "../components/PhasePipelineCard.vue";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";
import { useRouter } from "vue-router";

const router = useRouter();
const session = useSessionStore();
const { fullName } = storeToRefs(session);

const data = ref(null);
const loading = ref(true);
const error = ref("");

function pipelineMeta(key) {
	return OVERVIEW_PIPELINE_META[key] || { icon: MapPin, tone: "neutral" };
}

function navigateToBucket(bucket) {
	const phases = phasesFromBucket(bucket);
	const query = {};
	const phasesQuery = phasesToQuery(phases);
	if (phasesQuery) {
		query.phases = phasesQuery;
	}
	router.push({ path: "/shipments", query });
}

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
	router.push(`/shipments/${encodeURIComponent(name)}`);
}

onMounted(load);
</script>
