<template>
	<router-link
		:to="`/shipments/${encodeURIComponent(job.name)}`"
		class="sd-shipment-list-card"
		:class="{ 'sd-shipment-list-card--overdue': job.is_overdue }"
	>
		<div class="sd-shipment-list-card-main">
			<div class="sd-shipment-list-card-head">
				<div class="sd-shipment-list-card-identity">
					<div class="sd-shipment-list-card-primary">{{ primaryLabel }}</div>
					<div class="sd-shipment-list-card-cargo">{{ cargoLine }}</div>
				</div>
				<StatusBadge :status="job.status" />
			</div>

			<p v-if="job.current_comment" class="sd-shipment-list-card-headline">{{ job.current_comment }}</p>
			<p class="sd-shipment-list-card-meta sd-muted">{{ metaLine }}</p>

			<div class="sd-shipment-list-card-foot">
				<span class="sd-shipment-list-card-phase">{{ formatOperationalPhase(job) }}</span>
				<div class="sd-shipment-list-card-progress">
					<span class="sd-shipment-list-card-progress-value">
						{{ progressPercent }}%
					</span>
					<ProgressBar :percent="progressPercent" />
				</div>
			</div>
		</div>
	</router-link>
</template>

<script setup>
import { computed } from "vue";
import {
	formatOperationalPhase,
} from "../operationalPhases";
import {
	shipmentCargoLine,
	shipmentMetaLine,
	shipmentPrimaryLabel,
} from "../utils/shipmentList";
import ProgressBar from "./ProgressBar.vue";
import StatusBadge from "./StatusBadge.vue";

const props = defineProps({
	job: { type: Object, required: true },
});

const primaryLabel = computed(() => shipmentPrimaryLabel(props.job));
const cargoLine = computed(() => shipmentCargoLine(props.job));
const metaLine = computed(() => shipmentMetaLine(props.job));
const progressPercent = computed(
	() => props.job.client_progress_percent ?? props.job.milestone_percent ?? 0,
);
</script>
