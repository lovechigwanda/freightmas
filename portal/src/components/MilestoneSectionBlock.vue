<template>
	<div>
		<div v-if="!hideHead" class="sd-milestones-section-head">
			<span class="sd-milestones-section-title">{{ section.title }}</span>
			<span
				v-if="section.progress"
				class="sd-progress-badge"
				:class="progressTone(section.progress.percent)"
			>
				{{ section.progress.done }}/{{ section.progress.total }} &middot; {{ section.progress.percent }}%
			</span>
		</div>

		<template v-if="section.kind === 'sea_air'">
			<div class="sd-stage-grid sd-stage-grid-single">
				<div
					v-for="(stage, idx) in section.shipment_stages"
					:key="stage.label"
					class="sd-stage-row"
					:class="{ 'sd-stage-row--active': isActiveStage(section.shipment_stages, idx) }"
				>
					<span class="sd-stage-dot" :class="stage.done ? 'done' : 'pending'">
						<Check v-if="stage.done" :size="12" stroke-width="3" />
					</span>
					<span class="sd-stage-label">{{ stage.label }}</span>
					<span class="sd-stage-date">{{ stage.date ? formatDate(stage.date) : "Pending" }}</span>
				</div>
			</div>
		</template>

		<template v-else-if="section.kind === 'clearance_stages'">
			<ul class="sd-list sd-stage-list">
				<li
					v-for="st in section.stages"
					:key="st.name"
					:class="{ 'sd-stage-current': st.is_current }"
				>
					<span>
						{{ st.name }}
						<span v-if="st.is_current" class="sd-stage-badge">Current</span>
					</span>
					<span class="sd-muted">{{ st.done }}/{{ st.total }} &middot; {{ st.pct }}%</span>
				</li>
			</ul>
		</template>

		<template v-else-if="section.kind === 'clearance_checklist'">
			<div class="sd-stage-grid">
				<div
					v-for="(entry, idx) in section.entries"
					:key="entry.label"
					class="sd-stage-row"
					:class="{ 'sd-stage-row--active': isActiveEntry(section.entries, idx) }"
				>
					<span class="sd-stage-dot" :class="entry.is_completed ? 'done' : 'pending'">
						<Check v-if="entry.is_completed" :size="12" stroke-width="3" />
					</span>
					<span class="sd-stage-label">{{ entry.label }}</span>
					<span class="sd-stage-date">
						{{ entry.completed_on ? formatDate(entry.completed_on) : "Pending" }}
					</span>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { Check } from "@lucide/vue";
import { formatDate } from "../format";
import { progressTone } from "../utils/shipmentView";

defineProps({
	section: { type: Object, required: true },
	hideHead: { type: Boolean, default: false },
});

function isActiveStage(stages, idx) {
	const stage = stages[idx];
	if (!stage || stage.done) return false;
	return !stages.slice(0, idx).some((item) => !item.done);
}

function isActiveEntry(entries, idx) {
	const entry = entries[idx];
	if (!entry || entry.is_completed) return false;
	return !entries.slice(0, idx).some((item) => !item.is_completed);
}
</script>
