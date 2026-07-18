<template>
	<div class="sd-card cc-kpi" :class="tone">
		<div class="cc-kpi-icon">
			<component :is="icon" stroke-width="2" />
		</div>
		<div class="cc-kpi-text">
			<div class="sd-kpi-label">{{ label }}</div>
			<div class="sd-kpi-value" :class="tone">{{ value }}</div>
			<div v-if="sub" class="sd-kpi-sub">{{ sub }}</div>
		</div>
		<Sparkline v-if="trend && trend.length > 1" :values="trend" :color="sparkColor" :width="40" :height="24" class="cc-kpi-spark" />
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Activity } from "@lucide/vue";
import Sparkline from "./Sparkline.vue";

const props = defineProps({
	label: { type: String, required: true },
	value: { type: [String, Number], required: true },
	sub: { type: String, default: "" },
	tone: { type: String, default: "" }, // "", "warn", "danger", "good"
	icon: { type: [Object, Function], default: () => Activity },
	trend: { type: Array, default: () => [] },
});

const sparkColor = computed(() => {
	if (props.tone === "danger") return "#dc2626";
	if (props.tone === "warn") return "#d97706";
	if (props.tone === "good") return "#16a34a";
	return "#4f46e5";
});
</script>
