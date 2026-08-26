<template>
	<div class="sd-card sd-shipment-hero" :class="`sd-shipment-hero--${statusKey}`">
		<div class="sd-shipment-hero-main">
			<div class="sd-shipment-hero-status-row">
				<span class="sd-shipment-hero-label">{{ status.label }}</span>
				<span v-if="status.is_terminal && completedOn" class="sd-shipment-hero-date">
					{{ formatDate(completedOn) }}
				</span>
			</div>
			<p v-if="status.headline" class="sd-shipment-hero-headline">{{ status.headline }}</p>
			<p v-if="routeLine" class="sd-shipment-hero-route">{{ routeLine }}</p>
		</div>

		<div v-if="steps.length" class="sd-shipment-hero-steps">
			<div
				v-for="(step, idx) in steps"
				:key="step.id"
				class="sd-shipment-hero-step"
				:class="`sd-shipment-hero-step--${step.state}`"
			>
				<span class="sd-shipment-hero-step-marker">
					<Check v-if="step.state === 'done'" :size="12" stroke-width="3" />
					<span v-else-if="step.state === 'current'" class="sd-shipment-hero-step-dot"></span>
				</span>
				<span class="sd-shipment-hero-step-label">{{ step.label }}</span>
				<span
					v-if="idx < steps.length - 1"
					class="sd-shipment-hero-step-connector"
					:class="{ 'sd-shipment-hero-step-connector--done': step.state === 'done' }"
				></span>
			</div>
		</div>

		<div class="sd-shipment-hero-progress">
			<div class="sd-shipment-hero-progress-meta">
				<span class="sd-shipment-hero-progress-label">Journey progress</span>
				<span class="sd-shipment-hero-progress-value">{{ status.progress_percent }}%</span>
			</div>
			<ProgressBar :percent="status.progress_percent" />
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Check } from "@lucide/vue";
import { formatDate } from "../format";
import ProgressBar from "./ProgressBar.vue";

const props = defineProps({
	trackingView: { type: Object, required: true },
	header: { type: Object, default: null },
	shipmentDates: { type: Object, default: null },
});

const status = computed(
	() =>
		props.trackingView?.client_status || {
			label: props.trackingView?.banner?.status_label || "In progress",
			headline: props.trackingView?.banner?.latest_update || "",
			progress_percent: props.trackingView?.banner?.progress_percent || 0,
			is_terminal: props.trackingView?.banner?.status_key === "green",
		},
);

const statusKey = computed(() => props.trackingView?.banner?.status_key || "orange");

const steps = computed(() => props.trackingView?.steps || []);

const completedOn = computed(
	() => props.shipmentDates?.completed_on || props.shipmentDates?.ata || props.shipmentDates?.atd,
);

const routeLine = computed(() => {
	const h = props.header;
	if (!h) return "";
	const origin = h.port_of_loading || "–";
	const dest = h.destination || h.port_of_discharge || "–";
	const parts = [`${origin} → ${dest}`];
	if (h.direction) parts.push(h.direction);
	if (h.shipment_mode && h.shipment_type) {
		parts.push(`${h.shipment_mode} · ${h.shipment_type}`);
	}
	return parts.join(" · ");
});
</script>
