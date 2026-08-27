<template>
	<div class="sd-card sd-invoice-aging-strip">
		<button
			v-for="bucket in buckets"
			:key="bucket.key"
			type="button"
			class="sd-invoice-aging-bucket"
			:class="{
				active: activeBucket === bucket.key,
				'sd-invoice-aging-bucket--warn': bucket.key !== 'current' && bucket.amount,
			}"
			@click="$emit('select', bucket.key)"
		>
			<span class="sd-invoice-aging-bucket-label">{{ bucket.label }}</span>
			<span class="sd-invoice-aging-bucket-value">{{ formatMoney(bucket.amount) }}</span>
			<span class="sd-invoice-aging-bucket-count">{{ formatNumber(bucket.count) }} invoice(s)</span>
		</button>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { AGING_BUCKETS } from "../utils/invoiceList";
import { formatMoney, formatNumber } from "../format";

const props = defineProps({
	aging: { type: Object, required: true },
	activeBucket: { type: String, default: "" },
});

defineEmits(["select"]);

const buckets = computed(() =>
	AGING_BUCKETS.map((bucket) => ({
		...bucket,
		amount: props.aging?.[bucket.key]?.amount || 0,
		count: props.aging?.[bucket.key]?.count || 0,
	})),
);
</script>
