<template>
	<div>
		<div v-if="loading" class="sd-shipment-page">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 8" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<div v-else-if="detail" class="sd-shipment-page">
			<header class="sd-shipment-header">
				<router-link to="/shipments" class="sd-table-link">&larr; Back to Shipments</router-link>
				<div class="sd-shipment-header-main">
					<h1 class="sd-shipment-title">{{ detail.header.name }}</h1>
					<StatusBadge :status="detail.header.status" />
				</div>
				<p v-if="serviceTagLine" class="sd-shipment-subtitle">{{ serviceTagLine }}</p>
			</header>

			<TrackingBanner
				v-if="detail.tracking_view?.banner"
				:banner="detail.tracking_view.banner"
				:sections="detail.tracking_view.sections"
				:fallback-percent="detail.header.milestone_percent"
			/>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main">Shipment Details</span></div>
					<div class="sd-shipment-details-grid">
						<dl class="sd-shipment-details-col">
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">BL Number</dt>
								<dd>{{ detail.header.bl_number || "–" }}</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Route</dt>
								<dd>
									{{ detail.header.port_of_loading || "–" }} &rarr;
									{{ detail.header.destination || detail.header.port_of_discharge || "–" }}
								</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Direction</dt>
								<dd>{{ detail.header.direction || "–" }}</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Incoterms</dt>
								<dd>{{ detail.header.incoterms || "–" }}</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Booking Date</dt>
								<dd>{{ formatDate(detail.shipment_dates.booking_date) }}</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">ETD / ATD</dt>
								<dd>
									{{ formatDate(detail.shipment_dates.etd) }} &middot;
									{{ detail.shipment_dates.atd ? formatDate(detail.shipment_dates.atd) : "Pending" }}
								</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">ETA / ATA</dt>
								<dd>
									{{ formatDate(detail.shipment_dates.eta) }} &middot;
									{{ detail.shipment_dates.ata ? formatDate(detail.shipment_dates.ata) : "Pending" }}
								</dd>
							</div>
						</dl>
						<dl class="sd-shipment-details-col">
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Customer Ref</dt>
								<dd>{{ detail.header.customer_reference || "–" }}</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Mode / Type</dt>
								<dd>
									{{ detail.header.shipment_mode || "–" }} &middot; {{ detail.header.shipment_type || "–" }}
								</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Vessel / Flight</dt>
								<dd>{{ detail.header.vessel_flight_no || "–" }}</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Cargo</dt>
								<dd>
									{{ detail.header.cargo_description || "–" }}
									<span v-if="detail.header.cargo_count"> &middot; {{ detail.header.cargo_count }}</span>
								</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Discharge Date</dt>
								<dd>{{ formatDate(detail.shipment_dates.discharge_date) }}</dd>
							</div>
							<div class="sd-shipment-detail-row">
								<dt class="sd-muted">Completed On</dt>
								<dd>{{ formatDate(detail.shipment_dates.completed_on) }}</dd>
							</div>
						</dl>
					</div>
				</div>

				<ShipmentDocumentsCard
					:documents="documents"
					:loading="documentsLoading"
					:error="documentsError"
					:download-url="downloadUrl"
				/>
			</div>

			<ShipmentMilestonesCard
				:view="detail.tracking_view"
				:fallback-percent="detail.header.milestone_percent"
			/>

			<ShipmentCargoTable :view="detail.tracking_view" />

			<div class="sd-grid sd-grid-2">
				<ShipmentCommentsCard :updates="detail.tracking_view?.live_updates" />
				<ShipmentCompletionCard :section="completion" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { api } from "../api/shipments";
import { api as documentsApi } from "../api/documents";
import { formatDate } from "../format";
import { completionSection, serviceTags } from "../utils/shipmentView";
import StatusBadge from "../components/StatusBadge.vue";
import TrackingBanner from "../components/TrackingBanner.vue";
import ShipmentDocumentsCard from "../components/ShipmentDocumentsCard.vue";
import ShipmentMilestonesCard from "../components/ShipmentMilestonesCard.vue";
import ShipmentCargoTable from "../components/ShipmentCargoTable.vue";
import ShipmentCommentsCard from "../components/ShipmentCommentsCard.vue";
import ShipmentCompletionCard from "../components/ShipmentCompletionCard.vue";

const props = defineProps({ id: { type: String, required: true } });

const detail = ref(null);
const loading = ref(true);
const error = ref("");
const documents = ref(null);
const documentsLoading = ref(false);
const documentsError = ref("");

const serviceTagLine = computed(() => {
	if (!detail.value) return "";
	return serviceTags(detail.value.header, detail.value.tracking_view?.sections);
});

const completion = computed(() => completionSection(detail.value?.tracking_view?.sections));

async function load(jobName) {
	loading.value = true;
	error.value = "";
	documents.value = null;
	documentsError.value = "";
	documentsLoading.value = true;
	try {
		const [detailRes, docsRes] = await Promise.all([
			api.getJobDetail(jobName),
			documentsApi.getJobDocuments(jobName).catch((e) => {
				documentsError.value = e.message || "Failed to load documents.";
				return null;
			}),
		]);
		detail.value = detailRes;
		if (docsRes) {
			documents.value = docsRes;
		}
	} catch (e) {
		error.value = e.message || "Failed to load this shipment.";
	} finally {
		loading.value = false;
		documentsLoading.value = false;
	}
}

function downloadUrl(checklistRow) {
	return documentsApi.downloadDocumentUrl(props.id, checklistRow);
}

watch(() => props.id, (id) => id && load(id), { immediate: true });
</script>
