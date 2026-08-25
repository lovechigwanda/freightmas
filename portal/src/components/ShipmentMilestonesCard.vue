<template>
	<div class="sd-grid sd-grid-2 sd-milestones-row">
		<div class="sd-card">
			<div class="sd-card-title">
				<span class="sd-card-title-main">
					<span class="sd-card-title-icon"><ListChecks /></span>
					Milestones
				</span>
				<span class="sd-progress-badge" :class="progressTone(leftOverall.percent)">
					{{ leftOverall.done }}/{{ leftOverall.total }} &middot; {{ leftOverall.percent }}%
				</span>
			</div>
			<div class="sd-milestones-stack">
				<div
					v-for="section in leftSections"
					:key="section.title"
					class="sd-milestones-section"
				>
					<MilestoneSectionBlock :section="section" />
				</div>
			</div>
		</div>

		<div v-if="portSection" class="sd-card">
			<div class="sd-card-title">
				<span class="sd-card-title-main">Port Clearance</span>
				<span
					v-if="portSection.progress"
					class="sd-progress-badge"
					:class="progressTone(portSection.progress.percent)"
				>
					{{ portSection.progress.done }}/{{ portSection.progress.total }} &middot; {{ portSection.progress.percent }}%
				</span>
			</div>
			<MilestoneSectionBlock :section="portSection" :hide-head="true" />
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { ListChecks } from "@lucide/vue";
import {
	leftMilestoneSections,
	portMilestoneSection,
	progressTone,
} from "../utils/shipmentView";
import MilestoneSectionBlock from "./MilestoneSectionBlock.vue";

const props = defineProps({
	view: { type: Object, default: null },
});

const leftSections = computed(() => leftMilestoneSections(props.view?.sections));
const portSection = computed(() => portMilestoneSection(props.view?.sections));

const leftOverall = computed(() => {
	let done = 0;
	let total = 0;
	for (const section of leftSections.value) {
		done += section.progress?.done ?? 0;
		total += section.progress?.total ?? 0;
	}
	return {
		done,
		total,
		percent: total ? Math.round((done / total) * 100) : 0,
	};
});
</script>
