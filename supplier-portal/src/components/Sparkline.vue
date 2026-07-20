<template>
	<svg
		class="cc-sparkline"
		:width="width"
		:height="height"
		:viewBox="`0 0 ${width} ${height}`"
		preserveAspectRatio="none"
		role="img"
		aria-hidden="true"
	>
		<defs>
			<linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0%" :stop-color="color" stop-opacity="0.35" />
				<stop offset="100%" :stop-color="color" stop-opacity="0" />
			</linearGradient>
		</defs>
		<path v-if="areaPath" :d="areaPath" :fill="`url(#${gradientId})`" stroke="none" />
		<path v-if="linePath" :d="linePath" fill="none" :stroke="color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
		<circle v-if="lastPoint" :cx="lastPoint.x" :cy="lastPoint.y" r="2.5" :fill="color" />
	</svg>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	values: { type: Array, default: () => [] },
	width: { type: Number, default: 96 },
	height: { type: Number, default: 32 },
	color: { type: String, default: "#4f46e5" },
});

const gradientId = `cc-spark-${Math.random().toString(36).slice(2, 9)}`;

const coords = computed(() => {
	const vals = props.values.filter((v) => typeof v === "number" && !Number.isNaN(v));
	if (vals.length < 2) return [];
	const min = Math.min(...vals);
	const max = Math.max(...vals);
	const range = max - min || 1;
	const step = props.width / (vals.length - 1);
	const pad = 3;
	return vals.map((v, i) => ({
		x: i * step,
		y: pad + (1 - (v - min) / range) * (props.height - pad * 2),
	}));
});

const linePath = computed(() => {
	if (!coords.value.length) return "";
	return coords.value.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ");
});

const areaPath = computed(() => {
	if (!coords.value.length) return "";
	const first = coords.value[0];
	const last = coords.value[coords.value.length - 1];
	return `${linePath.value} L ${last.x.toFixed(2)} ${props.height} L ${first.x.toFixed(2)} ${props.height} Z`;
});

const lastPoint = computed(() => coords.value[coords.value.length - 1] || null);
</script>
