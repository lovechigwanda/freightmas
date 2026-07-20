<template>
	<div class="cc-skeleton" :style="{ width, height, borderRadius: radius }"></div>
</template>

<script setup>
defineProps({
	width: { type: String, default: "100%" },
	height: { type: String, default: "14px" },
	radius: { type: String, default: "" },
});
</script>
