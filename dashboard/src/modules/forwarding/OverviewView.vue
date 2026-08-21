<template>
	<div>
		<div v-if="loading" class="sd-phase-pipeline">
			<div class="sd-card sd-phase-pipeline-skeleton cc-skeleton" v-for="i in 7" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
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
						@click="$emit('navigate-bucket', bucket.key)"
					/>
				</div>
			</div>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card sd-jobs-status-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><PieChart /></span>
							Jobs by Status
						</span>
						<nav class="sd-tabs sd-jobs-scope-tabs">
							<button
								v-for="tab in jobScopeTabs"
								:key="tab.key"
								type="button"
								class="sd-tab"
								:class="{ active: jobScope === tab.key }"
								@click="jobScope = tab.key"
							>{{ tab.label }}</button>
						</nav>
					</div>
					<DonutChart
						:data="statusData"
						clickable
						@row-click="onStatusClick"
					/>
					<div class="sd-jobs-cargo-summary">
						<div class="sd-jobs-cargo-stat">
							<span class="sd-jobs-cargo-label">Containers</span>
							<span class="sd-jobs-cargo-value">{{ jobsSummary.containers }}</span>
						</div>
						<div class="sd-jobs-cargo-stat">
							<span class="sd-jobs-cargo-label">Parcels</span>
							<span class="sd-jobs-cargo-value">{{ jobsSummary.parcels }}</span>
						</div>
					</div>
					<table class="sd-table sd-jobs-direction-table" v-if="jobsSummary.by_direction.length">
						<thead>
							<tr>
								<th>Direction</th>
								<th class="sd-right">Jobs</th>
								<th class="sd-right">Containers</th>
								<th class="sd-right">Parcels</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in jobsSummary.by_direction" :key="row.direction">
								<td>{{ row.direction }}</td>
								<td class="sd-right">{{ row.jobs }}</td>
								<td class="sd-right">{{ row.containers }}</td>
								<td class="sd-right">{{ row.parcels }}</td>
							</tr>
						</tbody>
					</table>
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><TrendingUp /></span>
							Revenue &amp; Margin (last 6 months)
						</span>
						<Sparkline :values="revenueTrend" :color="theme.palette.spark.default" :width="90" :height="28" />
					</div>
					<table class="sd-table">
						<thead>
							<tr><th>Month</th><th class="sd-right">Shipments</th><th class="sd-right">Revenue</th><th class="sd-right">Margin</th></tr>
						</thead>
						<tbody>
							<tr v-for="row in data.monthly_trend" :key="row.period">
								<td>{{ row.period }}</td>
								<td class="sd-right">{{ row.shipment_count }}</td>
								<td class="sd-right">{{ formatMoney(row.revenue) }}</td>
								<td class="sd-right">{{ formatMoney(row.margin) }}</td>
							</tr>
						</tbody>
					</table>
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><Building2 /></span>
							Top Customers (Active Jobs)
						</span>
					</div>
					<ul class="sd-list">
						<li v-for="(row, idx) in data.top_customers" :key="row.customer">
							<span class="cc-list-label"><span class="cc-rank">{{ idx + 1 }}</span><span class="cc-list-text">{{ row.customer }}</span></span>
							<span class="sd-badge sd-badge-blue">{{ row.job_count }}</span>
						</li>
					</ul>
					<EmptyState v-if="!data.top_customers.length" :icon="Building2" title="No active jobs" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">
							<span class="sd-card-title-icon"><Route /></span>
							Top Corridors
						</span>
					</div>
					<ul class="sd-list">
						<li v-for="(row, idx) in data.top_corridors" :key="idx">
							<span class="cc-list-label"><span class="cc-rank">{{ idx + 1 }}</span><span class="cc-list-text">{{ row.port_of_loading }} &rarr; {{ row.port_of_discharge }}</span></span>
							<span class="sd-badge sd-badge-blue">{{ row.job_count }}</span>
						</li>
					</ul>
					<EmptyState v-if="!data.top_corridors.length" :icon="Route" title="No corridor data yet" />
				</div>
			</div>

			<div class="sd-card" style="margin-top: 16px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						<span class="sd-card-title-icon"><AlertCircle /></span>
						Recent Blockers / Exceptions
					</span>
				</div>
				<table class="sd-table" v-if="data.recent_blockers.length">
					<thead>
						<tr><th>Job</th><th>Customer</th><th>Status</th><th>Comment</th><th>Updated</th></tr>
					</thead>
					<tbody>
						<tr v-for="row in data.recent_blockers" :key="row.name">
							<td><button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button></td>
							<td>{{ row.customer }}</td>
							<td><StatusBadge :status="row.status" /></td>
							<td>{{ row.current_comment }}</td>
							<td class="sd-muted">{{ formatDate(row.last_updated_on) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="CheckCircle2" title="No open blockers logged" sub="Everything is tracking cleanly." />
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import {
	PieChart, TrendingUp, Building2, Route, AlertCircle, CheckCircle2,
} from "@lucide/vue";
import { api } from "./api";
import { useThemeStore } from "../../stores/theme";
import { formatMoney, formatDate, statusColor } from "../../format";
import { OVERVIEW_PIPELINE_META } from "./operationalPhases";
import StatusBadge from "../../components/StatusBadge.vue";
import PhasePipelineCard from "../../components/PhasePipelineCard.vue";
import DonutChart from "../../components/DonutChart.vue";
import Sparkline from "../../components/Sparkline.vue";
import EmptyState from "../../components/EmptyState.vue";
import { MapPin } from "@lucide/vue";

const emit = defineEmits(["open-job", "navigate-bucket", "navigate-status"]);

const theme = useThemeStore();
const loading = ref(true);
const error = ref("");
const data = ref(null);
const jobScope = ref("active");

const jobScopeTabs = [
	{ key: "active", label: "Active" },
	{ key: "all", label: "All Jobs" },
];

function pipelineMeta(key) {
	return OVERVIEW_PIPELINE_META[key] || { icon: MapPin, tone: "neutral" };
}

function jobsSummarySource() {
	if (!data.value?.jobs_summary) {
		return {
			by_status: data.value?.jobs_by_status || [],
			containers: 0,
			parcels: 0,
			by_direction: [],
		};
	}
	return data.value.jobs_summary[jobScope.value] || data.value.jobs_summary.all;
}

const jobsSummary = computed(() => {
	void jobScope.value;
	return jobsSummarySource();
});

const statusData = computed(() => {
	void theme.themeId;
	const summary = jobsSummary.value;
	return summary.by_status.map((row, idx) => ({
		label: row.status,
		value: row.count,
		color: statusColor(row.status, idx),
	}));
});

function onStatusClick(row) {
	if (!row?.label) return;
	emit("navigate-status", row.label);
}

const revenueTrend = computed(() => {
	if (!data.value) return [];
	return data.value.monthly_trend.map((row) => Number(row.revenue) || 0);
});

onMounted(async () => {
	try {
		data.value = await api.getOverview();
	} catch (e) {
		error.value = e.message || "Failed to load overview.";
	} finally {
		loading.value = false;
	}
});
</script>
