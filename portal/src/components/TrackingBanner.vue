<template>
	<div class="sd-card sd-shipment-banner" :class="`sd-tracking-banner--${banner.status_key}`">
		<div class="sd-shipment-banner-body">
			<div class="sd-shipment-banner-left">
				<h2 class="sd-shipment-banner-phase">{{ banner.operational_phase_label || banner.status_label }}</h2>
				<p v-if="banner.latest_update" class="sd-shipment-banner-update">{{ banner.latest_update }}</p>
			</div>
			<div class="sd-shipment-banner-right">
				<div class="sd-shipment-banner-progress-label">Overall progress</div>
				<div class="sd-shipment-banner-progress-row">
					<span class="sd-shipment-banner-progress-count">
						{{ overall.done }}/{{ overall.total }} &middot; {{ overall.percent }}%
					</span>
					<ProgressBar :percent="overall.percent" />
				</div>
				<div v-if="chips.length" class="sd-shipment-stage-chips">
					<span
						v-for="chip in chips"
						:key="chip.key"
						class="sd-shipment-stage-chip"
						:class="{ 'sd-shipment-stage-chip--active': chip.active }"
					>
						{{ chip.label }}
						<span class="sd-shipment-stage-chip-count">{{ chip.done }}/{{ chip.total }}</span>
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { markActiveStageChip, overallProgress, stageChips } from "../utils/shipmentView";
import ProgressBar from "./ProgressBar.vue";

const props = defineProps({
	banner: { type: Object, required: true },
	sections: { type: Array, default: () => [] },
	fallbackPercent: { type: Number, default: 0 },
});

const overall = computed(() =>
	overallProgress(props.sections, props.banner.progress_percent ?? props.fallbackPercent),
);

const chips = computed(() => markActiveStageChip(stageChips(props.sections)));
</script>
