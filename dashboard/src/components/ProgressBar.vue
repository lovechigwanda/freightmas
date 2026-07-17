<template>
	<span class="sd-progress" :title="`${percent}%`">
		<span :style="{ width: percent + '%', background: color }"></span>
	</span>
	<span class="sd-muted" style="font-size: 11px; margin-left: 6px">{{ percent }}%</span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	percent: { type: Number, default: 0 },
});

const color = computed(() => {
	if (props.percent >= 100) return "#16a34a";
	if (props.percent >= 50) return "#2e6da4";
	if (props.percent > 0) return "#d97706";
	return "#dc2626";
});
</script>
