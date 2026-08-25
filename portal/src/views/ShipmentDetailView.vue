<template>
	<div>
		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 6" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="detail">
			<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
				<router-link to="/shipments" class="sd-table-link">&larr; Back to Shipments</router-link>
				<span style="font-weight: 600; font-size: 15px;">{{ detail.header.name }}</span>
				<StatusBadge :status="detail.header.status" />
			</div>

			<nav class="sd-tabs">
				<button class="sd-tab" :class="{ active: tab === 'overview' }" @click="setTab('overview')">Overview</button>
				<button class="sd-tab" :class="{ active: tab === 'tracking' }" @click="setTab('tracking')">Tracking</button>
				<button class="sd-tab" :class="{ active: tab === 'documents' }" @click="setTab('documents')">Documents</button>
			</nav>

			<div v-if="tab === 'overview'" class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main">Shipment Details</span></div>
					<ul class="sd-list">
						<li><span class="sd-muted">Route</span><span>{{ detail.header.port_of_loading || "–" }} &rarr; {{ detail.header.destination || detail.header.port_of_discharge || "–" }}</span></li>
						<li><span class="sd-muted">Mode / Type</span><span>{{ detail.header.shipment_mode || "–" }} &middot; {{ detail.header.shipment_type || "–" }}</span></li>
						<li><span class="sd-muted">Direction</span><span>{{ detail.header.direction || "–" }}</span></li>
						<li><span class="sd-muted">Vessel / Flight</span><span>{{ detail.header.vessel_flight_no || "–" }}</span></li>
						<li><span class="sd-muted">BL Number</span><span>{{ detail.header.bl_number || "–" }}</span></li>
						<li><span class="sd-muted">Incoterms</span><span>{{ detail.header.incoterms || "–" }}</span></li>
						<li><span class="sd-muted">Customer Reference</span><span>{{ detail.header.customer_reference || "–" }}</span></li>
						<li><span class="sd-muted">Cargo</span><span>{{ detail.header.cargo_description || "–" }}<span v-if="detail.header.cargo_count"> &middot; {{ detail.header.cargo_count }}</span></span></li>
					</ul>
				</div>

				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main">Dates</span></div>
					<ul class="sd-list">
						<li><span class="sd-muted">Booking Date</span><span>{{ formatDate(detail.shipment_dates.booking_date) }}</span></li>
						<li><span class="sd-muted">ETD / ATD</span><span>{{ formatDate(detail.shipment_dates.etd) }} &middot; {{ detail.shipment_dates.atd ? formatDate(detail.shipment_dates.atd) : "Pending" }}</span></li>
						<li><span class="sd-muted">ETA / ATA</span><span>{{ formatDate(detail.shipment_dates.eta) }} &middot; {{ detail.shipment_dates.ata ? formatDate(detail.shipment_dates.ata) : "Pending" }}</span></li>
						<li><span class="sd-muted">Discharge Date</span><span>{{ formatDate(detail.shipment_dates.discharge_date) }}</span></li>
						<li><span class="sd-muted">Completed On</span><span>{{ formatDate(detail.shipment_dates.completed_on) }}</span></li>
					</ul>
					<div v-if="detail.header.current_comment" class="sd-muted" style="margin-top: 12px; font-size: 13px;">
						Latest update: {{ detail.header.current_comment }}
					</div>
				</div>
			</div>

			<TrackingTab v-else-if="tab === 'tracking'" :view="detail.tracking_view" />

			<template v-else-if="tab === 'documents'">
				<div v-if="documentsLoading" class="sd-card">
					<div class="cc-row-skeleton cc-skeleton" v-for="i in 4" :key="i"></div>
				</div>
				<div v-else-if="documentsError" class="sd-state" style="color: var(--sd-red)">{{ documentsError }}</div>
				<template v-else-if="documents">
					<div class="sd-card" style="margin-bottom: 14px;">
						<div class="sd-card-title"><span class="sd-card-title-main">Outgoing</span></div>
						<p class="sd-muted cc-documents-intro">Documents shared with you by your account team.</p>
						<table class="sd-table" v-if="documents.outgoing.length">
							<thead>
								<tr>
									<th>Document</th>
									<th>File</th>
									<th>Submitted</th>
									<th>Verified</th>
									<th></th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in documents.outgoing" :key="row.name">
									<td>{{ row.document_label }}</td>
									<td class="sd-muted">{{ row.file_name || "–" }}</td>
									<td>{{ formatDate(row.date_submitted) }}</td>
									<td>{{ row.is_verified ? formatDate(row.date_verified) : "–" }}</td>
									<td>
										<a
											class="sd-table-link"
											:href="downloadUrl(row.name)"
											target="_blank"
											rel="noopener"
										>
											Download
										</a>
									</td>
								</tr>
							</tbody>
						</table>
						<EmptyState v-else :icon="FileText" title="No outgoing documents yet" sub="Your team has not shared any documents for this shipment." />
					</div>

					<div class="sd-card">
						<div class="sd-card-title"><span class="sd-card-title-main">Incoming</span></div>
						<p class="sd-muted cc-documents-intro">Documents you submit to your account team.</p>
						<table class="sd-table" v-if="documents.incoming.length">
							<thead>
								<tr>
									<th>Document</th>
									<th>File</th>
									<th>Submitted</th>
									<th></th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in documents.incoming" :key="row.name">
									<td>{{ row.document_label }}</td>
									<td class="sd-muted">{{ row.file_name || "–" }}</td>
									<td>{{ formatDate(row.date_submitted) }}</td>
									<td>
										<a
											class="sd-table-link"
											:href="downloadUrl(row.name)"
											target="_blank"
											rel="noopener"
										>
											Download
										</a>
									</td>
								</tr>
							</tbody>
						</table>
						<EmptyState v-else :icon="Upload" title="No incoming documents yet" sub="Documents you upload will appear here." />
					</div>
				</template>
			</template>
		</template>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { FileText, Upload } from "@lucide/vue";
import { api } from "../api/shipments";
import { api as documentsApi } from "../api/documents";
import { formatDate } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";
import TrackingTab from "../components/TrackingTab.vue";

const props = defineProps({ id: { type: String, required: true } });

const detail = ref(null);
const loading = ref(true);
const error = ref("");
const tab = ref("overview");
const documents = ref(null);
const documentsLoading = ref(false);
const documentsError = ref("");

async function load(jobName) {
	loading.value = true;
	error.value = "";
	documents.value = null;
	documentsError.value = "";
	try {
		detail.value = await api.getJobDetail(jobName);
		if (tab.value === "documents") {
			await loadDocuments(jobName);
		}
	} catch (e) {
		error.value = e.message || "Failed to load this shipment.";
	} finally {
		loading.value = false;
	}
}

async function loadDocuments(jobName) {
	documentsLoading.value = true;
	documentsError.value = "";
	try {
		documents.value = await documentsApi.getJobDocuments(jobName);
	} catch (e) {
		documentsError.value = e.message || "Failed to load documents.";
	} finally {
		documentsLoading.value = false;
	}
}

function setTab(nextTab) {
	tab.value = nextTab;
	if (nextTab === "documents" && props.id && !documents.value && !documentsLoading.value) {
		loadDocuments(props.id);
	}
}

function downloadUrl(checklistRow) {
	return documentsApi.downloadDocumentUrl(props.id, checklistRow);
}

watch(() => props.id, (id) => id && load(id), { immediate: true });
</script>

<style scoped>
.cc-documents-intro {
	margin: -6px 0 14px;
	font-size: 13px;
}
</style>
