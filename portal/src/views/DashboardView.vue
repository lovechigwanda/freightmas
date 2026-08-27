<template>
	<div>
		<div v-if="loading" class="sd-phase-pipeline">
			<div class="sd-card sd-phase-pipeline-skeleton cc-skeleton" v-for="i in 7" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<DashboardCommandHeader
				:active-count="data.active_count"
				:delayed-count="data.delayed_count"
				:outstanding-amount="data.outstanding_amount"
				:full-name="fullName"
				style="margin-bottom: 18px;"
			/>

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

			<div class="sd-grid sd-grid-kpi sd-dashboard-kpi" style="margin-bottom: 18px;">
				<router-link to="/shipments?status=In%20Progress" class="sd-dashboard-kpi-link">
					<KpiCard label="Active Shipments" :value="formatNumber(data.active_count)" tone="good" :icon="Ship" />
				</router-link>
				<router-link to="/shipments?status=In%20Progress" class="sd-dashboard-kpi-link">
					<KpiCard
						label="Delayed"
						:value="formatNumber(data.delayed_count)"
						:tone="data.delayed_count ? 'danger' : 'good'"
						:icon="AlertTriangle"
					/>
				</router-link>
				<router-link to="/shipments?status=In%20Progress" class="sd-dashboard-kpi-link">
					<KpiCard
						label="Arriving Soon"
						:value="formatNumber(data.arriving_soon_count)"
						tone="good"
						:icon="Package"
					/>
				</router-link>
				<router-link to="/invoices" class="sd-dashboard-kpi-link">
					<KpiCard
						label="Outstanding"
						:value="formatMoney(data.outstanding_amount)"
						:tone="data.outstanding_amount ? 'warn' : 'good'"
						:icon="Wallet"
					/>
				</router-link>
				<router-link to="/invoices" class="sd-dashboard-kpi-link">
					<KpiCard
						label="Overdue Invoices"
						:value="formatMoney(data.overdue_amount)"
						:tone="data.overdue_amount ? 'danger' : 'good'"
						:icon="Receipt"
					/>
				</router-link>
			</div>

			<div class="sd-card sd-active-tracking-cta" style="margin-bottom: 18px;">
				<div class="sd-active-tracking-cta-body">
					<div>
						<div class="sd-active-tracking-cta-title">Active tracking report</div>
						<p class="sd-muted sd-active-tracking-cta-copy">
							{{ formatNumber(data.active_count) }} active shipment(s)
							<span v-if="data.delayed_count"> · {{ formatNumber(data.delayed_count) }} delayed</span>
						</p>
					</div>
					<div class="sd-active-tracking-cta-actions">
						<router-link to="/shipments?status=In%20Progress" class="sd-table-link">View all &rarr;</router-link>
						<a class="sd-table-link" :href="trackingExcelUrl" rel="noopener">Download Excel</a>
						<a class="sd-table-link" :href="trackingPdfUrl" rel="noopener">Download PDF</a>
					</div>
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
						<div v-if="data.in_motion_jobs.length" class="sd-dashboard-in-motion-list">
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
import { computed, ref, onMounted } from "vue";
import { storeToRefs } from "pinia";
import {
	Ship,
	Wallet,
	Receipt,
	MapPin,
	AlertTriangle,
	Package,
} from "@lucide/vue";
import { api } from "../api/dashboard";
import { api as shipmentsApi } from "../api/shipments";
import { formatMoney, formatNumber } from "../format";
import { useSessionStore } from "../stores/session";
import {
	OVERVIEW_PIPELINE_META,
	phasesFromBucket,
	phasesToQuery,
} from "../operationalPhases";
import DashboardAttentionQueue from "../components/DashboardAttentionQueue.vue";
import DashboardCommandHeader from "../components/DashboardCommandHeader.vue";
import DashboardFinancialSnapshot from "../components/DashboardFinancialSnapshot.vue";
import KpiCard from "../components/KpiCard.vue";
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

const trackingExcelUrl = computed(() =>
	shipmentsApi.exportTrackingReportUrl({ status: "In Progress" }),
);
const trackingPdfUrl = computed(() =>
	shipmentsApi.exportTrackingReportPdfUrl({ status: "In Progress" }),
);

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
.sd-dashboard-kpi-link {
	text-decoration: none;
	color: inherit;
	display: block;
}

.sd-dashboard-main {
	grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	gap: 14px;
	align-items: start;
}

.sd-dashboard-in-motion-card {
	height: 100%;
}

.sd-dashboard-in-motion-list {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.sd-dashboard-in-motion-item :deep(.sd-shipment-list-card) {
	display: block;
}

@media (max-width: 900px) {
	.sd-dashboard-main {
		grid-template-columns: 1fr;
	}
}
</style>
