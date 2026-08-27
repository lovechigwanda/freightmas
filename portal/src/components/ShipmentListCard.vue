<template>
	<router-link
		:to="`/shipments/${encodeURIComponent(job.name)}`"
		class="sd-shipment-list-card"
		:class="{ 'sd-shipment-list-card--overdue': job.is_overdue }"
	>
		<div class="sd-shipment-list-card-row sd-shipment-list-card-row--top">
			<div class="sd-shipment-list-card-top-main">
				<span class="sd-shipment-list-card-primary">{{ primaryLabel }}</span>
				<span class="sd-shipment-list-card-cargo-inline">{{ cargoLine }}</span>
			</div>
			<div class="sd-shipment-list-card-top-aside">
				<StatusBadge :status="job.status" />
				<span class="sd-shipment-list-card-progress-value">{{ progressPercent }}%</span>
			</div>
		</div>

		<div class="sd-shipment-list-card-row sd-shipment-list-card-row--bottom">
			<p class="sd-shipment-list-card-subline sd-muted">{{ subline }}</p>
			<div class="sd-shipment-list-card-progress-inline">
				<ProgressBar :percent="progressPercent" :show-label="false" />
			</div>
		</div>
	</router-link>
</template>

<script setup>
import { computed } from "vue";
import {
	shipmentCargoLine,
	shipmentCompactSubline,
	shipmentPrimaryLabel,
} from "../utils/shipmentList";
import ProgressBar from "./ProgressBar.vue";
import StatusBadge from "./StatusBadge.vue";

const props = defineProps({
	job: { type: Object, required: true },
});

const primaryLabel = computed(() => shipmentPrimaryLabel(props.job));
const cargoLine = computed(() => shipmentCargoLine(props.job));
const subline = computed(() => shipmentCompactSubline(props.job));
const progressPercent = computed(
	() => props.job.client_progress_percent ?? props.job.milestone_percent ?? 0,
);
</script>
