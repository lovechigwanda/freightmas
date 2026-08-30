<template>
	<tr
		class="sd-shipment-table-row"
		:class="{ 'cc-row-overdue': job.is_overdue }"
		@click="goToShipment"
	>
		<td class="sd-shipment-table-shipment">
			<span class="sd-shipment-table-primary">{{ primaryLabel }}</span>
			<span v-if="job.is_overdue" class="sd-shipment-alert-dot" aria-hidden="true"></span>
		</td>
		<td v-if="showEquip" class="sd-shipment-table-equip">{{ equipmentLabel }}</td>
		<td class="sd-shipment-table-milestone">
			<span
				class="sd-shipment-table-phase"
				:class="`sd-shipment-table-phase--${phaseTone}`"
			>{{ milestone.phase }}</span>
			<template v-if="milestone.comment">
				<span class="sd-shipment-table-sep">&middot;</span>
				<span class="sd-shipment-table-comment">{{ milestone.comment }}</span>
			</template>
			<template v-if="milestone.shortDate">
				<span class="sd-shipment-table-sep">&middot;</span>
				<span class="sd-shipment-table-date">{{ milestone.shortDate }}</span>
			</template>
		</td>
		<td
			class="sd-shipment-table-eta"
			:class="`sd-shipment-table-eta--${etaAta.urgency}`"
		>
			<template v-if="etaAta.kind !== 'none'">
				<span class="sd-shipment-table-eta-label">{{ etaAta.label }}</span>
				<span class="sd-shipment-table-eta-date">{{ etaAta.display }}</span>
			</template>
			<span v-else>{{ etaAta.display }}</span>
		</td>
		<td class="sd-shipment-table-progress">
			<div class="sd-shipment-table-progress-inner">
				<ProgressBar
					:percent="progressPercent"
					:show-label="false"
					:tone="job.is_overdue ? 'alert' : 'default'"
				/>
				<span class="sd-shipment-table-progress-value">{{ progressPercent }}%</span>
			</div>
		</td>
	</tr>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import {
	shipmentEquipmentLabel,
	shipmentEtaAtaDisplay,
	shipmentMilestoneLine,
	shipmentPhaseTone,
	shipmentPrimaryLabel,
} from "../utils/shipmentList";
import ProgressBar from "./ProgressBar.vue";

const props = defineProps({
	job: { type: Object, required: true },
	showEquip: { type: Boolean, default: true },
});

const router = useRouter();

const primaryLabel = computed(() => shipmentPrimaryLabel(props.job));
const equipmentLabel = computed(() => shipmentEquipmentLabel(props.job));
const milestone = computed(() => shipmentMilestoneLine(props.job));
const phaseTone = computed(() => shipmentPhaseTone(props.job));
const etaAta = computed(() => shipmentEtaAtaDisplay(props.job));
const progressPercent = computed(
	() => props.job.client_progress_percent ?? props.job.milestone_percent ?? 0,
);

function goToShipment() {
	router.push(`/shipments/${encodeURIComponent(props.job.name)}`);
}
</script>
