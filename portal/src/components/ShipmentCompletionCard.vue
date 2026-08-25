<template>
	<div class="sd-card">
		<div class="sd-card-title">
			<span class="sd-card-title-main">Completion</span>
			<span
				v-if="section?.progress"
				class="sd-progress-badge"
				:class="progressTone(section.progress.percent)"
			>
				{{ section.progress.done }}/{{ section.progress.total }} &middot; {{ section.progress.percent }}%
			</span>
		</div>
		<div class="sd-stage-group">
			<div class="sd-stage-grid sd-stage-grid-single">
				<div class="sd-stage-row sd-stage-row-completion">
					<span class="sd-stage-dot" :class="section?.completed ? 'done' : 'pending'">
						<Check v-if="section?.completed" :size="12" stroke-width="3" />
					</span>
					<span class="sd-stage-label">Completed</span>
					<span class="sd-stage-date">
						{{ section?.completed_on ? formatDate(section.completed_on) : "Pending" }}
					</span>
				</div>
			</div>
		</div>
		<div class="sd-completion-date">
			<span class="sd-muted">Completed On</span>
			<span>{{ completedOnLabel }}</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Check } from "@lucide/vue";
import { formatDate } from "../format";
import { progressTone } from "../utils/shipmentView";

const props = defineProps({
	section: { type: Object, default: null },
	completedOn: { type: String, default: "" },
});

const completedOnLabel = computed(() => {
	const value = props.section?.completed_on || props.completedOn;
	return value ? formatDate(value) : "–";
});
</script>
