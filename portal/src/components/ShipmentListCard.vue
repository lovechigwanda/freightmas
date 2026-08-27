<template>
	<router-link
		:to="`/shipments/${encodeURIComponent(job.name)}`"
		class="sd-shipment-list-card"
		:class="{ 'sd-shipment-list-card--overdue': job.is_overdue }"
	>
		<div class="sd-shipment-list-card-row sd-shipment-list-card-row--primary">
			<div class="sd-shipment-list-card-identity">
				<component :is="modeIcon" class="sd-shipment-list-card-mode" :size="16" stroke-width="2" />
				<span class="sd-shipment-list-card-primary">{{ primaryLabel }}</span>
				<span v-for="chip in cargoChips" :key="chip.label" class="sd-shipment-list-card-chip">
					{{ chip.label }}
				</span>
				<span v-if="job.is_overdue" class="sd-shipment-list-card-chip sd-shipment-list-card-chip--warn">
					Delayed
				</span>
			</div>
			<div class="sd-shipment-list-card-signals">
				<span
					class="sd-shipment-list-card-phase"
					:class="`sd-shipment-list-card-phase--${phaseTone}`"
				>
					{{ phaseLabel }}
				</span>
				<span
					class="sd-shipment-list-card-eta"
					:class="`sd-shipment-list-card-eta--${eta.urgency}`"
				>
					{{ eta.display }}
				</span>
			</div>
		</div>

		<div class="sd-shipment-list-card-row sd-shipment-list-card-row--secondary">
			<p class="sd-shipment-list-card-headline sd-muted">{{ headline }}</p>
			<div class="sd-shipment-list-card-progress-wrap">
				<ProgressBar :percent="progressPercent" :show-label="false" />
				<span class="sd-shipment-list-card-progress-value">{{ progressPercent }}%</span>
			</div>
		</div>
	</router-link>
</template>

<script setup>
import { computed } from "vue";
import {
	shipmentCargoChips,
	shipmentEtaLabel,
	shipmentHeadline,
	shipmentModeIcon,
	shipmentPhaseLabel,
	shipmentPhaseTone,
	shipmentPrimaryLabel,
} from "../utils/shipmentList";
import ProgressBar from "./ProgressBar.vue";

const props = defineProps({
	job: { type: Object, required: true },
});

const primaryLabel = computed(() => shipmentPrimaryLabel(props.job));
const modeIcon = computed(() => shipmentModeIcon(props.job));
const cargoChips = computed(() => shipmentCargoChips(props.job));
const phaseLabel = computed(() => shipmentPhaseLabel(props.job));
const phaseTone = computed(() => shipmentPhaseTone(props.job));
const eta = computed(() => shipmentEtaLabel(props.job));
const headline = computed(() => shipmentHeadline(props.job));
const progressPercent = computed(
	() => props.job.client_progress_percent ?? props.job.milestone_percent ?? 0,
);
</script>
