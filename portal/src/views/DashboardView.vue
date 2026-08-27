<template>
	<div>
		<div v-if="loading" class="sd-phase-pipeline">
			<div class="sd-card sd-phase-pipeline-skeleton cc-skeleton" v-for="i in 7" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<DashboardCommandHeader
				:attention-count="data.attention_count"
				:overdue-amount="data.financial_snapshot.overdue_amount"
				:full-name="fullName"
				style="margin-bottom: 18px;"
			/>

			<div style="margin-bottom: 18px;">
				<div class="sd-pipeline-section-head">
					<h3 class="sd-pipeline-section-title">Shipment Pipeline</h3>
					<span v-if="data.arriving_soon_count" class="sd-muted sd-pipeline-section-meta">
						{{ formatNumber(data.arriving_soon_count) }} arriving within 14 days
					</span>
				</div>
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

			<div class="sd-grid sd-dashboard-main" style="margin-bottom: 18px;">
				<DashboardAttentionQueue :items="data.attention_items" />

				<div class="sd-dashboard-in-motion">
					<div class="sd-card sd-dashboard-in-motion-card">
						<div class="sd-card-title">
							<span class="sd-card-title-main">In motion</span>
							<router-link to="/shipments?status=In%20Progress" class="sd-table-link" style="font-size: 12px;">
								View all &rarr;
							</router-link>
						</div>
						<div v-if="data.in_motion_jobs.length" class="sd-shipment-list">
							<ShipmentListCard
								v-for="job in data.in_motion_jobs"
								:key="job.name"
								:job="job"
								class="sd-dashboard-in-motion-item"
							/>
						</div>
						<EmptyState
							v-else
							:icon="Ship"
							title="No active shipments"
							sub="Your in-progress shipments will appear here."
						/>
					</div>
				</div>
			</div>

			<DashboardFinancialSnapshot :snapshot="data.financial_snapshot" />
		</template>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { Ship, MapPin } from "@lucide/vue";
import { api } from "../api/dashboard";
import { formatNumber } from "../format";
import { useSessionStore } from "../stores/session";
import {
	OVERVIEW_PIPELINE_META,
	phasesFromBucket,
	phasesToQuery,
} from "../operationalPhases";
import DashboardAttentionQueue from "../components/DashboardAttentionQueue.vue";
import DashboardCommandHeader from "../components/DashboardCommandHeader.vue";
import DashboardFinancialSnapshot from "../components/DashboardFinancialSnapshot.vue";
import PhasePipelineCard from "../components/PhasePipelineCard.vue";
import ShipmentListCard from "../components/ShipmentListCard.vue";
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

onMounted(load);
</script>

<style scoped>
.sd-dashboard-main {
	grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	gap: 14px;
	align-items: start;
}

.sd-dashboard-in-motion-card {
	height: 100%;
}

.sd-pipeline-section-head {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 12px;
	margin-bottom: 10px;
}

.sd-pipeline-section-meta {
	font-size: 12px;
	white-space: nowrap;
}

@media (max-width: 900px) {
	.sd-dashboard-main {
		grid-template-columns: 1fr;
	}

	.sd-pipeline-section-head {
		flex-direction: column;
		align-items: flex-start;
		gap: 4px;
	}
}
</style>
