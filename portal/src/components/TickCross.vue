<template>
	<span v-if="value" class="cc-tick"><Check :size="15" stroke-width="2.5" /></span>
	<span v-else class="cc-cross"><X :size="15" stroke-width="2.5" /></span>
</template>

<script setup>
import { Check, X } from "@lucide/vue";

defineProps({
	value: { type: Boolean, default: false },
});
</script>
