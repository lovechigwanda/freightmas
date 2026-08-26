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
					<span v-if="serviceTagLine" class="sd-shipment-subtitle">{{ serviceTagLine }}</span>
				</div>
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

				<ShipmentDocumentsCard
					:documents="documents"
					:loading="documentsLoading"
					:error="documentsError"
					:download-url="downloadUrl"
					compact-empty
				/>
			</div>

			<ShipmentCargoTable :containers="detail.tracking_view?.containers || []" />

			<ShipmentCommentsCard
				v-if="showActivity"
				:updates="detail.tracking_view?.live_updates"
				:limit="5"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { api } from "../api/shipments";
import { api as documentsApi } from "../api/documents";
import { serviceTags } from "../utils/shipmentView";
import StatusBadge from "../components/StatusBadge.vue";
import ShipmentHero from "../components/ShipmentHero.vue";
import ShipmentFactStrip from "../components/ShipmentFactStrip.vue";
import JourneyTimeline from "../components/JourneyTimeline.vue";
import ShipmentDocumentsCard from "../components/ShipmentDocumentsCard.vue";
import ShipmentCargoTable from "../components/ShipmentCargoTable.vue";
import ShipmentCommentsCard from "../components/ShipmentCommentsCard.vue";

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

const showActivity = computed(() => {
	const updates = detail.value?.tracking_view?.live_updates || [];
	const isTerminal = detail.value?.tracking_view?.client_status?.is_terminal;
	return updates.length > 0 && !isTerminal;
});

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
