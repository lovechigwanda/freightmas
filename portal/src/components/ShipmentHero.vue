<template>
	<div class="sd-card sd-shipment-hero" :class="`sd-shipment-hero--${statusKey}`">
		<div class="sd-shipment-hero-body">
			<div class="sd-shipment-hero-left">
				<div class="sd-shipment-hero-status-line">
					<span class="sd-shipment-hero-label">{{ status.label }}</span>
					<template v-if="statusDetail">
						<span class="sd-shipment-hero-sep">&middot;</span>
						<span class="sd-shipment-hero-detail">{{ statusDetail }}</span>
					</template>
					<template v-if="statusDate">
						<span class="sd-shipment-hero-sep">&middot;</span>
						<span class="sd-shipment-hero-detail">{{ statusDate }}</span>
					</template>
					<span
						v-if="status.is_terminal && completedOn"
						class="sd-shipment-hero-sep"
					>&middot;</span>
					<span
						v-if="status.is_terminal && completedOn"
						class="sd-shipment-hero-detail"
					>{{ formatDate(completedOn) }}</span>
				</div>
				<p v-if="routeLine" class="sd-shipment-hero-route">{{ routeLine }}</p>
			</div>

			<div v-if="etaAta.label" class="sd-shipment-hero-right">
				<div class="sd-shipment-hero-eta">
					<span class="sd-shipment-hero-eta-label">{{ etaAta.label }}</span>
					<span class="sd-shipment-hero-eta-date">{{ etaAta.display }}</span>
				</div>
			</div>
		</div>

		<div v-if="steps.length" class="sd-shipment-hero-steps-wrap">
			<div class="sd-shipment-hero-steps">
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
			<span class="sd-shipment-hero-complete">{{ status.progress_percent }}% complete</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Check } from "@lucide/vue";
import { formatDate, formatDateShort } from "../format";

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

const statusDetail = computed(() => {
	if (status.value.is_terminal) return "";
	return status.value.headline || "";
});

const statusDate = computed(() => {
	if (status.value.is_terminal || !props.header?.last_updated_on) return "";
	return formatDateShort(props.header.last_updated_on);
});

const routeLine = computed(() => {
	const h = props.header;
	if (!h) return "";
	const origin = h.port_of_loading || "–";
	const dest = h.destination || h.port_of_discharge || "–";
	return `${origin} → ${dest}`;
});

const etaAta = computed(() => {
	const h = props.header;
	const d = props.shipmentDates || {};
	const isExport = h?.direction === "Export";
	const actualDate = isExport ? d.atd : d.ata;
	const actualLabel = isExport ? "ATD" : "ATA";
	const estimatedDate = isExport ? d.etd : d.eta;
	const estimatedLabel = isExport ? "ETD" : "ETA";

	if (actualDate) {
		return { label: actualLabel, display: formatDate(actualDate) };
	}
	if (estimatedDate) {
		return { label: estimatedLabel, display: formatDate(estimatedDate) };
	}
	return { label: "", display: "" };
});
</script>
