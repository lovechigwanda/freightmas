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
	if (props.percent >= 100) return "#15803d";
	if (props.percent >= 50) return "#4f46e5";
	if (props.percent > 0) return "#b45309";
	return "#b91c1c";
});
</script>
