<template>
	<router-link
		:to="`/quotations/${encodeURIComponent(quotation.name)}`"
		class="sd-invoice-list-card sd-quotation-list-card"
		:class="{ 'sd-quotation-list-card--expired': quotation.is_expired }"
	>
		<div class="sd-invoice-list-card-row sd-invoice-list-card-row--primary">
			<div class="sd-invoice-list-card-identity">
				<FileText class="sd-invoice-list-card-mode" :size="16" stroke-width="2" />
				<span class="sd-invoice-list-card-primary">{{ quotation.name }}</span>
				<span v-if="quotation.customer_reference" class="sd-invoice-list-card-chip">
					{{ quotation.customer_reference }}
				</span>
				<span
					v-if="quotation.is_expired"
					class="sd-invoice-list-card-chip sd-invoice-list-card-chip--warn"
				>
					Expired
				</span>
			</div>
			<div class="sd-invoice-list-card-balance-col">
				<span class="sd-invoice-list-card-balance-label">Total</span>
				<span class="sd-invoice-list-card-balance-value">{{ formatMoney(quotation.grand_total) }}</span>
			</div>
		</div>

		<div class="sd-invoice-list-card-row sd-invoice-list-card-row--secondary">
			<p class="sd-invoice-list-card-meta">
				<span class="sd-invoice-list-card-meta-name">{{ secondaryMeta }}</span>
				<span v-if="validityLabel" class="sd-invoice-list-card-due"> · {{ validityLabel }}</span>
			</p>
			<div style="display: flex; gap: 10px; align-items: center;">
				<StatusBadge :status="quotation.client_status || quotation.workflow_state" />
				<router-link
					v-if="shipmentLink"
					class="sd-table-link sd-invoice-list-card-shipment-link"
					:to="shipmentLink"
					@click.stop
				>
					View shipment
				</router-link>
			</div>
		</div>
	</router-link>
</template>

<script setup>
import { computed } from "vue";
import { FileText } from "@lucide/vue";
import { formatDate, formatMoney } from "../format";
import StatusBadge from "./StatusBadge.vue";

const props = defineProps({
	quotation: { type: Object, required: true },
});

const secondaryMeta = computed(() => {
	const parts = [];
	if (props.quotation.job_type) parts.push(props.quotation.job_type);
	if (props.quotation.job_description) parts.push(props.quotation.job_description);
	return parts.join(" · ") || props.quotation.customer_name || "Quotation";
});

const validityLabel = computed(() => {
	if (!props.quotation.valid_till) return "";
	return props.quotation.is_expired
		? `Expired ${formatDate(props.quotation.valid_till)}`
		: `Valid until ${formatDate(props.quotation.valid_till)}`;
});

const shipmentLink = computed(() =>
	props.quotation.job_name ? `/shipments/${encodeURIComponent(props.quotation.job_name)}` : null,
);
</script>
