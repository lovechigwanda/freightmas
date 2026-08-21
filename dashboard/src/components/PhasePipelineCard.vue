<template>
	<div class="sd-phase-pipeline-item">
		<button type="button" class="sd-phase-card" :class="tone" :title="cardTitle" @click="$emit('click')">
			<div class="sd-phase-card-head">
				<div class="sd-phase-card-icon">
					<component :is="icon" stroke-width="2" />
				</div>
				<div class="sd-phase-card-count">{{ count }}</div>
			</div>
			<div class="sd-phase-card-label">{{ label }}</div>
		</button>
		<ChevronRight v-if="showConnector" :size="16" stroke-width="2" class="sd-phase-connector" aria-hidden="true" />
	</div>
</template>

<script setup>
import { computed } from "vue";
import { ChevronRight } from "@lucide/vue";
import { MapPin } from "@lucide/vue";

const props = defineProps({
	label: { type: String, required: true },
	title: { type: String, default: "" },
	count: { type: Number, default: 0 },
	tone: { type: String, default: "default" },
	icon: { type: [Object, Function], default: () => MapPin },
	showConnector: { type: Boolean, default: false },
});

defineEmits(["click"]);

const cardTitle = computed(() => props.title || props.label);
</script>
