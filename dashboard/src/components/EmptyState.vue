<template>
	<div class="cc-empty">
		<component :is="icon" class="cc-empty-icon" stroke-width="1.5" />
		<div class="cc-empty-title">{{ title }}</div>
		<div v-if="sub" class="cc-empty-sub">{{ sub }}</div>
	</div>
</template>

<script setup>
import { Inbox } from "@lucide/vue";

defineProps({
	icon: { type: [Object, Function], default: () => Inbox },
	title: { type: String, required: true },
	sub: { type: String, default: "" },
});
</script>
