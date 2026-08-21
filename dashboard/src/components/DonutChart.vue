<template>
	<div class="cc-donut-wrap">
		<svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" role="img" aria-hidden="true">
			<circle
				:cx="size / 2"
				:cy="size / 2"
				:r="radius"
				fill="none"
				:stroke="trackColor"
				:stroke-width="thickness"
			/>
			<circle
				v-for="seg in segments"
				:key="seg.label"
				:cx="size / 2"
				:cy="size / 2"
				:r="radius"
				fill="none"
				:stroke="seg.color"
				:stroke-width="thickness"
				stroke-linecap="butt"
				:stroke-dasharray="`${seg.length} ${circumference - seg.length}`"
				:stroke-dashoffset="-seg.offset"
				:transform="`rotate(-90 ${size / 2} ${size / 2})`"
			/>
			<text
				:x="size / 2"
				:y="size / 2 - 4"
				text-anchor="middle"
				class="cc-donut-total"
			>{{ total }}</text>
			<text
				:x="size / 2"
				:y="size / 2 + 13"
				text-anchor="middle"
				class="cc-donut-total-label"
			>total</text>
		</svg>
		<div class="cc-donut-legend">
			<div
				v-for="row in data"
				:key="row.label"
				class="cc-donut-legend-row"
				:class="{ 'cc-donut-legend-row-clickable': clickable }"
				:role="clickable ? 'button' : undefined"
				:tabindex="clickable ? 0 : undefined"
				@click="onRowClick(row)"
				@keydown.enter.prevent="onRowClick(row)"
			>
				<span class="cc-donut-legend-dot" :style="{ background: row.color }"></span>
				<span class="cc-donut-legend-label">{{ row.label }}</span>
				<span class="cc-donut-legend-value">{{ row.value }}</span>
			</div>
			<div v-if="!data.length" class="sd-muted" style="font-size: 12px">No data.</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	data: { type: Array, default: () => [] }, // [{ label, value, color }]
	size: { type: Number, default: 108 },
	thickness: { type: Number, default: 14 },
	trackColor: { type: String, default: "#eef0f5" },
	clickable: { type: Boolean, default: false },
});

const emit = defineEmits(["row-click"]);

function onRowClick(row) {
	if (!props.clickable || !Number(row.value)) return;
	emit("row-click", row);
}

const radius = computed(() => props.size / 2 - props.thickness / 2 - 2);
const circumference = computed(() => 2 * Math.PI * radius.value);
const total = computed(() => props.data.reduce((sum, d) => sum + (Number(d.value) || 0), 0));

const segments = computed(() => {
	let offset = 0;
	const t = total.value || 1;
	return props.data
		.filter((d) => Number(d.value) > 0)
		.map((d) => {
			const length = (Number(d.value) / t) * circumference.value;
			const seg = { label: d.label, color: d.color, length, offset };
			offset += length;
			return seg;
		});
});
</script>

<style scoped>
.cc-donut-total {
	font-size: 20px;
	font-weight: 700;
	fill: var(--sd-text);
	font-family: inherit;
}

.cc-donut-total-label {
	font-size: 9px;
	fill: var(--sd-text-muted);
	text-transform: uppercase;
	letter-spacing: 0.04em;
	font-family: inherit;
}

.cc-donut-legend-row-clickable {
	cursor: pointer;
	border-radius: 6px;
	margin: 0 -6px;
	padding: 2px 6px;
	transition: background 0.12s ease;
}

.cc-donut-legend-row-clickable:hover {
	background: var(--sd-surface-alt);
}
</style>
