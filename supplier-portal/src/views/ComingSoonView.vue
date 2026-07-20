<template>
	<div class="cc-coming-soon">
		<div class="cc-coming-soon-icon">
			<component :is="NAV_ICONS[icon] || Wrench" :size="28" stroke-width="1.75" />
		</div>
		<h2>{{ moduleName }}</h2>
		<p>{{ moduleName }} is coming soon.</p>
	</div>
</template>

<script setup>
import { Wrench } from "@lucide/vue";
import { NAV_ICONS } from "../icons";

defineProps({
	moduleName: { type: String, required: true },
	icon: { type: String, default: "" },
});
</script>
