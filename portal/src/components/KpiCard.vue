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
import { useThemeStore } from "../stores/theme";
import Sparkline from "./Sparkline.vue";

const props = defineProps({
	label: { type: String, required: true },
	value: { type: [String, Number], required: true },
	sub: { type: String, default: "" },
	tone: { type: String, default: "" }, // "", "warn", "danger", "good"
	icon: { type: [Object, Function], default: () => Activity },
	trend: { type: Array, default: () => [] },
});

const theme = useThemeStore();

const sparkColor = computed(() => {
	void theme.themeId;
	const spark = theme.palette.spark;
	if (props.tone === "danger") return spark.danger;
	if (props.tone === "warn") return spark.warn;
	if (props.tone === "good") return spark.good;
	return spark.default;
});
</script>
