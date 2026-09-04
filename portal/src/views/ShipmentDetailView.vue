<template>
	<div>
		<div v-if="loading" class="sd-shipment-page">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 8" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<div v-else-if="detail" class="sd-shipment-page">
			<header class="sd-shipment-header">
				<router-link to="/shipments" class="sd-table-link">&larr; Shipments</router-link>
				<h1 class="sd-shipment-title">{{ detail.header.name }}</h1>
				<StatusBadge :status="detail.header.status" />
			</header>

			<ShipmentHero
				:tracking-view="detail.tracking_view"
				:header="detail.header"
				:shipment-dates="detail.shipment_dates"
			/>

			<ShipmentFactStrip :header="detail.header" :shipment-dates="detail.shipment_dates" />

			<div class="sd-shipment-main-grid">
				<JourneyTimeline
					:journey="detail.tracking_view?.journey || []"
					:is-terminal="detail.tracking_view?.client_status?.is_terminal"
				/>

				<div class="sd-shipment-sidebar">
					<ShipmentQuotationsCard
						:quotations="quotations"
						:loading="quotationsLoading"
						:error="quotationsError"
						compact-empty
					/>
					<ShipmentInvoicesCard
						:invoices="invoices"
						:loading="invoicesLoading"
						:error="invoicesError"
						compact-empty
					/>
					<ShipmentDocumentsCard
						:documents="documents"
						:loading="documentsLoading"
						:error="documentsError"
						:download-url="downloadUrl"
						:job-name="id"
						compact-empty
						@refresh="reloadDocuments"
					/>
				</div>
			</div>

			<ShipmentCargoTable :containers="detail.tracking_view?.containers || []" />
		</div>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { api } from "../api/shipments";
import { api as documentsApi } from "../api/documents";
import { api as invoicesApi } from "../api/invoices";
import { api as quotationsApi } from "../api/quotations";
import StatusBadge from "../components/StatusBadge.vue";
import ShipmentHero from "../components/ShipmentHero.vue";
import ShipmentFactStrip from "../components/ShipmentFactStrip.vue";
import JourneyTimeline from "../components/JourneyTimeline.vue";
import ShipmentDocumentsCard from "../components/ShipmentDocumentsCard.vue";
import ShipmentInvoicesCard from "../components/ShipmentInvoicesCard.vue";
import ShipmentQuotationsCard from "../components/ShipmentQuotationsCard.vue";
import ShipmentCargoTable from "../components/ShipmentCargoTable.vue";

const props = defineProps({ id: { type: String, required: true } });

const detail = ref(null);
const loading = ref(true);
const error = ref("");
const documents = ref(null);
const documentsLoading = ref(false);
const documentsError = ref("");
const invoices = ref([]);
const invoicesLoading = ref(false);
const invoicesError = ref("");
const quotations = ref([]);
const quotationsLoading = ref(false);
const quotationsError = ref("");

async function load(jobName) {
	loading.value = true;
	error.value = "";
	documents.value = null;
	documentsError.value = "";
	documentsLoading.value = true;
	invoices.value = [];
	invoicesError.value = "";
	invoicesLoading.value = true;
	quotations.value = [];
	quotationsError.value = "";
	quotationsLoading.value = true;
	try {
		const [detailRes, docsRes, invRes, quoteRes] = await Promise.all([
			api.getJobDetail(jobName),
			documentsApi.getJobDocuments(jobName).catch((e) => {
				documentsError.value = e.message || "Failed to load documents.";
				return null;
			}),
			invoicesApi.getJobInvoices(jobName).catch((e) => {
				invoicesError.value = e.message || "Failed to load invoices.";
				return null;
			}),
			quotationsApi.getJobQuotations(jobName).catch((e) => {
				quotationsError.value = e.message || "Failed to load quotations.";
				return null;
			}),
		]);
		detail.value = detailRes;
		if (docsRes) {
			documents.value = docsRes;
		}
		if (invRes) {
			invoices.value = invRes.invoices || [];
		}
		if (quoteRes) {
			quotations.value = quoteRes.quotations || [];
		}
	} catch (e) {
		error.value = e.message || "Failed to load this shipment.";
	} finally {
		loading.value = false;
		documentsLoading.value = false;
		invoicesLoading.value = false;
		quotationsLoading.value = false;
	}
}

function downloadUrl(checklistRow) {
	return documentsApi.downloadDocumentUrl(props.id, checklistRow);
}

async function reloadDocuments() {
	if (!props.id) return;
	documentsLoading.value = true;
	documentsError.value = "";
	try {
		documents.value = await documentsApi.getJobDocuments(props.id);
	} catch (e) {
		documentsError.value = e.message || "Failed to load documents.";
	} finally {
		documentsLoading.value = false;
	}
}

watch(() => props.id, (id) => id && load(id), { immediate: true });
</script>
