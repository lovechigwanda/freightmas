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
	</div>
</template>

<script setup>
import { Check } from "@lucide/vue";
import { formatDate } from "../format";
import { progressTone } from "../utils/shipmentView";

defineProps({
	section: { type: Object, default: null },
});
</script>
