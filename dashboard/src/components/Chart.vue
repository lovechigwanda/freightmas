<template>
	<div class="cc-chart" :style="{ height }">
		<div v-if="!ready" class="cc-chart-loading cc-skeleton"></div>
		<div ref="el" class="cc-chart-canvas" :style="{ opacity: ready ? 1 : 0 }"></div>
	</div>
</template>

<script setup>
import { ref, shallowRef, onMounted, onBeforeUnmount, watch, nextTick } from "vue";

// Thin adapter over ECharts. Views never import ECharts directly - they pass a
// plain `option` object and this component lazy-loads the library, applies the
// Command Center's shared theme defaults, and manages init / resize / dispose.
// Swapping the charting engine later means touching only this file + the loader.
const props = defineProps({
	// A full ECharts option object. The component deep-merges a few themed
	// defaults (font, grid, tooltip, palette) underneath it.
	option: { type: Object, required: true },
	height: { type: String, default: "320px" },
	// Colour ramp; defaults to the dashboard palette (indigo-led).
	palette: { type: Array, default: null },
});

const PALETTE = ["#4f46e5", "#0d9488", "#d97706", "#16a34a", "#dc2626", "#7c3aed", "#0891b2", "#94a3b8"];

const el = ref(null);
const ready = ref(false);
const chart = shallowRef(null);
let echarts = null;
let ro = null;

function cssVar(name, fallback) {
	if (typeof window === "undefined") return fallback;
	const v = getComputedStyle(document.documentElement).getPropertyValue(name);
	return (v && v.trim()) || fallback;
}

function themedOption(option) {
	const textMuted = cssVar("--sd-text-muted", "#64748b");
	const border = cssVar("--sd-border", "#e2e8f0");
	const surface = cssVar("--sd-surface", "#ffffff");
	const text = cssVar("--sd-text", "#0f172a");
	const fontFamily = "'Inter Variable', Inter, system-ui, sans-serif";

	return {
		color: props.palette || PALETTE,
		textStyle: { fontFamily, color: textMuted },
		grid: { left: 8, right: 12, top: 24, bottom: 8, containLabel: true, ...(option.grid || {}) },
		tooltip: {
			trigger: "axis",
			backgroundColor: surface,
			borderColor: border,
			borderWidth: 1,
			textStyle: { color: text, fontFamily, fontSize: 12 },
			...(option.tooltip || {}),
		},
		...option,
	};
}

async function ensureChart() {
	if (chart.value) return;
	// Dynamic import keeps ECharts in its own lazy chunk, loaded only when a
	// chart first mounts - the always-loaded dashboard.js entry stays lean.
	const mod = await import("../echartsLoader");
	echarts = mod.getECharts();
	await nextTick();
	if (!el.value) return;
	chart.value = echarts.init(el.value, null, { renderer: "canvas" });
	ro = new ResizeObserver(() => chart.value && chart.value.resize());
	ro.observe(el.value);
	ready.value = true;
}

async function render() {
	await ensureChart();
	if (chart.value) {
		chart.value.setOption(themedOption(props.option), { notMerge: true });
	}
}

onMounted(render);

watch(() => props.option, render, { deep: true });

onBeforeUnmount(() => {
	if (ro && el.value) ro.unobserve(el.value);
	ro = null;
	if (chart.value) {
		chart.value.dispose();
		chart.value = null;
	}
});
</script>

<style scoped>
.cc-chart {
	position: relative;
	width: 100%;
}

.cc-chart-canvas {
	width: 100%;
	height: 100%;
	transition: opacity 0.2s ease;
}

.cc-chart-loading {
	position: absolute;
	inset: 0;
	border-radius: var(--sd-radius-sm, 8px);
}
</style>
