<template>
	<div class="sd-card sd-tracking-summary">
		<div class="sd-tracking-summary-stats">
			<div class="sd-tracking-summary-stat">
				<span class="sd-tracking-summary-value">{{ formatNumber(summary.active_count) }}</span>
				<span class="sd-tracking-summary-label">Active</span>
			</div>
			<div class="sd-tracking-summary-stat" :class="{ 'sd-tracking-summary-stat--warn': summary.delayed_count }">
				<span class="sd-tracking-summary-value">{{ formatNumber(summary.delayed_count) }}</span>
				<span class="sd-tracking-summary-label">Delayed</span>
			</div>
			<div class="sd-tracking-summary-stat">
				<span class="sd-tracking-summary-value">{{ formatNumber(summary.at_port_count) }}</span>
				<span class="sd-tracking-summary-label">At port</span>
			</div>
			<div class="sd-tracking-summary-stat">
				<span class="sd-tracking-summary-value">{{ formatNumber(summary.arriving_soon_count) }}</span>
				<span class="sd-tracking-summary-label">Arriving soon</span>
			</div>
		</div>
		<p v-if="showFilteredHint" class="sd-tracking-summary-filtered sd-muted">
			Showing {{ formatNumber(summary.filtered_count) }} shipment(s) matching your filters.
		</p>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { formatNumber } from "../format";

const props = defineProps({
	summary: { type: Object, required: true },
	hasFilters: { type: Boolean, default: false },
});

const showFilteredHint = computed(
	() => props.hasFilters && props.summary.filtered_count !== props.summary.active_count,
);
</script>
