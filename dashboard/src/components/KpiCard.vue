<template>
	<div class="sd-card sd-kpi">
		<div class="sd-kpi-label">{{ label }}</div>
		<div class="sd-kpi-value" :class="tone">{{ value }}</div>
		<div v-if="sub" class="sd-kpi-sub">{{ sub }}</div>
	</div>
</template>

<script setup>
defineProps({
	label: { type: String, required: true },
	value: { type: [String, Number], required: true },
	sub: { type: String, default: "" },
	tone: { type: String, default: "" }, // "", "warn", "danger"
});
</script>
