<template>
	<div class="sd-card sd-fact-strip">
		<div v-for="fact in facts" :key="fact.label" class="sd-fact-strip-item">
			<span class="sd-fact-strip-label">{{ fact.label }}</span>
			<span class="sd-fact-strip-value">{{ fact.value }}</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { formatDate } from "../format";

const props = defineProps({
	header: { type: Object, required: true },
	shipmentDates: { type: Object, default: () => ({}) },
});

const facts = computed(() => {
	const h = props.header;
	const d = props.shipmentDates || {};
	return [
		{ label: "BL Number", value: h.bl_number || "–" },
		{ label: "Customer Ref", value: h.customer_reference || "–" },
		{
			label: "ETD / ATD",
			value: `${formatDate(d.etd)} · ${d.atd ? formatDate(d.atd) : "Pending"}`,
		},
		{
			label: "ETA / ATA",
			value: `${formatDate(d.eta)} · ${d.ata ? formatDate(d.ata) : "Pending"}`,
		},
		{
			label: "Cargo",
			value: [h.cargo_description, h.cargo_count].filter(Boolean).join(" · ") || "–",
		},
		{ label: "Discharge", value: formatDate(d.discharge_date) },
	];
});
</script>
