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
					label="Active Shipments"
					:value="formatNumber(data.active_count)"
					tone="good"
					:icon="Ship"
				/>
				<KpiCard
					label="Delayed"
					:value="formatNumber(data.delayed_count)"
					:tone="data.delayed_count ? 'danger' : 'good'"
					:icon="AlertTriangle"
				/>
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
				<KpiCard
					label="Paid (YTD)"
					:value="formatMoney(data.paid_ytd)"
					tone="good"
					:icon="CheckCircle2"
				/>
			</div>

			<div class="sd-grid sd-grid-2 cc-dashboard-split" style="margin-bottom: 18px;">
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">Recent Shipments</span>
						<router-link to="/shipments" class="sd-table-link" style="font-size: 12px;">View all &rarr;</router-link>
					</div>
					<table class="sd-table" v-if="data.recent_jobs.length">
						<thead>
							<tr>
								<th>Job / Reference</th>
								<th>Phase</th>
								<th>Progress</th>
								<th>ETA</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="job in data.recent_jobs"
								:key="job.name"
								:class="{ 'cc-row-overdue': job.is_overdue }"
							>
								<td>
									<button class="sd-table-link" @click="openJob(job.name)">{{ job.name }}</button>
									<div class="sd-muted" style="font-size: 12px;">{{ job.customer_reference || "–" }}</div>
									<div v-if="job.current_comment" class="cc-dashboard-comment">{{ job.current_comment }}</div>
								</td>
								<td>{{ formatOperationalPhase(job) }}</td>
								<td><ProgressBar :percent="job.milestone_percent" /></td>
								<td>{{ formatDate(job.eta) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="Ship" title="No shipments yet" sub="Your active shipments will show up here." />
				</div>

				<div class="cc-dashboard-side">
					<div class="sd-card" style="margin-bottom: 14px;">
						<div class="sd-card-title">
							<span class="sd-card-title-main">Needs Attention</span>
						</div>
						<ul v-if="data.needs_attention.length" class="sd-list cc-dashboard-feed">
							<li v-for="job in data.needs_attention" :key="job.name">
								<button class="sd-table-link" @click="openJob(job.name)">{{ job.name }}</button>
								<div class="sd-muted" style="font-size: 12px;">
									{{ job.direction === "Import" ? "ETA" : "ETD" }}
									{{ formatDate(job.eta || job.etd) }}
									<span v-if="job.current_comment"> &middot; {{ job.current_comment }}</span>
								</div>
							</li>
						</ul>
						<EmptyState
							v-else
							:icon="CheckCircle2"
							title="No delayed shipments"
							sub="All active shipments are on schedule."
						/>
					</div>

					<div class="sd-card">
						<div class="sd-card-title">
							<span class="sd-card-title-main">Arriving Soon</span>
						</div>
						<ul v-if="data.arriving_soon.length" class="sd-list cc-dashboard-feed">
							<li v-for="job in data.arriving_soon" :key="job.name">
								<button class="sd-table-link" @click="openJob(job.name)">{{ job.name }}</button>
								<div class="sd-muted" style="font-size: 12px;">
									ETA {{ formatDate(job.eta) }}
									&middot; {{ job.port_of_loading || "–" }} &rarr; {{ job.destination || job.port_of_discharge || "–" }}
								</div>
							</li>
						</ul>
						<EmptyState
							v-else
							:icon="Package"
							title="Nothing arriving soon"
							sub="No import shipments due in the next 14 days."
						/>
					</div>
				</div>
			</div>

			<div class="sd-grid cc-dashboard-feeds">
				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">Recent Updates</span>
					</div>
					<ul v-if="data.recent_updates.length" class="sd-list cc-dashboard-feed">
						<li v-for="(item, idx) in data.recent_updates" :key="idx">
							<div style="display: flex; justify-content: space-between; gap: 8px;">
								<button class="sd-table-link" @click="openJob(item.job_name)">{{ item.job_name }}</button>
								<span class="sd-muted" style="font-size: 12px; white-space: nowrap;">{{ formatDateTime(item.date) }}</span>
							</div>
							<div style="font-size: 13px; margin-top: 2px;">{{ item.event }}</div>
							<div v-if="item.source" class="sd-muted" style="font-size: 12px;">via {{ item.source }}</div>
						</li>
					</ul>
					<EmptyState v-else :icon="History" title="No tracking updates yet" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">Recent Documents</span>
					</div>
					<ul v-if="data.recent_documents.length" class="sd-list cc-dashboard-feed">
						<li v-for="doc in data.recent_documents" :key="doc.name">
							<div>{{ doc.document_label }}</div>
							<div class="sd-muted" style="font-size: 12px;">
								<button class="sd-table-link" @click="openJob(doc.job_name)">{{ doc.job_name }}</button>
								<span v-if="doc.date_submitted"> &middot; {{ formatDate(doc.date_submitted) }}</span>
							</div>
							<a
								class="sd-table-link"
								style="font-size: 12px;"
								:href="downloadDocumentUrl(doc.job_name, doc.name)"
								target="_blank"
								rel="noopener"
							>
								Download
							</a>
						</li>
					</ul>
					<EmptyState v-else :icon="FileText" title="No documents shared yet" />
				</div>

				<div class="sd-card">
					<div class="sd-card-title">
						<span class="sd-card-title-main">Recent Invoices</span>
						<router-link to="/invoices" class="sd-table-link" style="font-size: 12px;">View all &rarr;</router-link>
					</div>
					<table class="sd-table" v-if="data.recent_invoices.length">
						<thead>
							<tr>
								<th>Invoice</th>
								<th>Shipment</th>
								<th>Due</th>
								<th>Amount</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="inv in data.recent_invoices" :key="inv.name">
								<td>
									<router-link class="sd-table-link" :to="`/invoices/${encodeURIComponent(inv.name)}`">
										{{ inv.name }}
									</router-link>
								</td>
								<td>{{ inv.job_name || "–" }}</td>
								<td>{{ formatDate(inv.due_date) }}</td>
								<td>{{ formatMoney(inv.grand_total) }}</td>
							</tr>
						</tbody>
					</table>
					<EmptyState v-else :icon="Receipt" title="No invoices yet" />
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { storeToRefs } from "pinia";
import {
	Ship,
	Wallet,
	Receipt,
	MapPin,
	AlertTriangle,
	CheckCircle2,
	History,
	FileText,
	Package,
} from "@lucide/vue";
import { api } from "../api/dashboard";
import { api as documentsApi } from "../api/documents";
import { formatDate, formatDateTime, formatMoney, formatNumber } from "../format";
import { useSessionStore } from "../stores/session";
import {
	OVERVIEW_PIPELINE_META,
	formatOperationalPhase,
	phasesFromBucket,
	phasesToQuery,
} from "../operationalPhases";
import KpiCard from "../components/KpiCard.vue";
import PhasePipelineCard from "../components/PhasePipelineCard.vue";
import ProgressBar from "../components/ProgressBar.vue";
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

function downloadDocumentUrl(jobName, checklistRow) {
	return documentsApi.downloadDocumentUrl(jobName, checklistRow);
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

<style scoped>
.cc-dashboard-split {
	align-items: start;
}

.cc-dashboard-side {
	display: flex;
	flex-direction: column;
}

.cc-dashboard-comment {
	font-size: 12px;
	color: var(--sd-text-muted);
	margin-top: 4px;
	max-width: 280px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.cc-dashboard-feed li {
	display: block;
	padding: 8px 0;
}

.cc-dashboard-feed li + li {
	border-top: 1px solid var(--sd-border-soft);
}
</style>
