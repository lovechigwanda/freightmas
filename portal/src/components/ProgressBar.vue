<template>
	<span class="sd-progress" :title="`${percent}%`">
		<span
			class="sd-progress-fill"
			:class="fillClass"
			:style="{ width: percent + '%' }"
		></span>
	</span>
	<span v-if="showLabel" class="sd-muted sd-progress-label">{{ percent }}%</span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	percent: { type: Number, default: 0 },
	showLabel: { type: Boolean, default: true },
	tone: { type: String, default: "default" },
});

const fillClass = computed(() => {
	if (props.tone === "alert") return "sd-progress-fill--alert";
	if (props.percent >= 100) return "sd-progress-fill--complete";
	if (props.percent >= 50) return "sd-progress-fill--progress";
	if (props.percent > 0) return "sd-progress-fill--started";
	return "sd-progress-fill--none";
});
</script>
