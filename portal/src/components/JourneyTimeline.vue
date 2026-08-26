<template>
	<div class="sd-card sd-journey-timeline">
		<div class="sd-card-title">
			<span class="sd-card-title-main">
				<span class="sd-card-title-icon"><Route /></span>
				Shipment Journey
			</span>
		</div>

		<div class="sd-journey-phases">
			<div
				v-for="phase in phases"
				:key="phase.id"
				class="sd-journey-phase"
				:class="{
					'sd-journey-phase--done': phase.state === 'done',
					'sd-journey-phase--current': phase.state === 'current',
					'sd-journey-phase--expanded': isExpanded(phase),
				}"
			>
				<button
					type="button"
					class="sd-journey-phase-head"
					:aria-expanded="isExpanded(phase)"
					@click="togglePhase(phase.id)"
				>
					<span class="sd-journey-phase-marker" :class="`sd-journey-phase-marker--${phase.state}`">
						<Check v-if="phase.state === 'done'" :size="14" stroke-width="3" />
					</span>
					<span class="sd-journey-phase-text">
						<span class="sd-journey-phase-title">{{ phase.title }}</span>
						<span class="sd-journey-phase-summary">{{ phase.summary }}</span>
					</span>
					<span v-if="phase.state === 'current'" class="sd-journey-phase-badge">Current</span>
					<ChevronDown
						class="sd-journey-phase-chevron"
						:class="{ 'sd-journey-phase-chevron--open': isExpanded(phase) }"
						:size="18"
					/>
				</button>

				<div v-show="isExpanded(phase)" class="sd-journey-phase-body">
					<MilestoneSectionBlock
						v-if="phase.section && phase.section.kind !== 'completion'"
						:section="phase.section"
						:hide-head="true"
					/>
					<div v-else-if="phase.section?.kind === 'completion'" class="sd-journey-completion">
						<div class="sd-stage-row">
							<span class="sd-stage-dot" :class="phase.section.completed ? 'done' : 'pending'">
								<Check v-if="phase.section.completed" :size="12" stroke-width="3" />
							</span>
							<span class="sd-stage-label">Shipment completed</span>
							<span class="sd-stage-date">
								{{
									phase.section.completed_on
										? formatDate(phase.section.completed_on)
										: phase.state === "done"
											? "Complete"
											: "Pending"
								}}
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Check, ChevronDown, Route } from "@lucide/vue";
import { formatDate } from "../format";
import MilestoneSectionBlock from "./MilestoneSectionBlock.vue";

const props = defineProps({
	journey: { type: Array, default: () => [] },
	isTerminal: { type: Boolean, default: false },
});

const expanded = ref(new Set());

const phases = computed(() => props.journey || []);

watch(
	phases,
	(journey) => {
		const next = new Set();
		const current = journey.find((phase) => phase.state === "current");
		if (current) {
			next.add(current.id);
		} else if (journey.length && !props.isTerminal) {
			next.add(journey[0].id);
		}
		expanded.value = next;
	},
	{ immediate: true },
);

function isExpanded(phase) {
	return expanded.value.has(phase.id);
}

function togglePhase(id) {
	const next = new Set(expanded.value);
	if (next.has(id)) {
		next.delete(id);
	} else {
		next.add(id);
	}
	expanded.value = next;
}
</script>
