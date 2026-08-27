<template>
	<article
		class="sd-invoice-list-card"
		:class="{
			'sd-invoice-list-card--overdue': invoice.is_overdue,
			'sd-invoice-list-card--credit': isCredit,
		}"
	>
		<div class="sd-invoice-list-card-main">
			<div class="sd-invoice-list-card-head">
				<div class="sd-invoice-list-card-identity">
					<router-link
						class="sd-invoice-list-card-primary"
						:to="`/invoices/${encodeURIComponent(invoice.name)}`"
					>
						{{ primaryLabel }}
					</router-link>
					<div class="sd-invoice-list-card-context">{{ contextLine }}</div>
				</div>
				<div class="sd-invoice-list-card-balance">
					<span class="sd-invoice-list-card-balance-label">{{ balanceLabel }}</span>
					<span class="sd-invoice-list-card-balance-value">{{ balanceAmount }}</span>
				</div>
			</div>

			<div class="sd-invoice-list-card-foot">
				<span class="sd-muted sd-invoice-list-card-meta">{{ metaLine }}</span>
				<div class="sd-invoice-list-card-actions">
					<StatusBadge :status="invoice.status" />
					<router-link
						v-if="shipmentLink"
						class="sd-table-link sd-invoice-list-card-shipment-link"
						:to="shipmentLink"
					>
						View shipment
					</router-link>
				</div>
			</div>
		</div>
	</article>
</template>

<script setup>
import { computed } from "vue";
import StatusBadge from "./StatusBadge.vue";
import {
	invoiceBalanceAmount,
	invoiceBalanceLabel,
	invoiceContextLine,
	invoiceIsCredit,
	invoiceMetaLine,
	invoicePrimaryLabel,
} from "../utils/invoiceList";

const props = defineProps({
	invoice: { type: Object, required: true },
});

const primaryLabel = computed(() => invoicePrimaryLabel(props.invoice));
const contextLine = computed(() => invoiceContextLine(props.invoice));
const metaLine = computed(() => invoiceMetaLine(props.invoice));
const balanceLabel = computed(() => invoiceBalanceLabel(props.invoice));
const balanceAmount = computed(() => invoiceBalanceAmount(props.invoice));
const isCredit = computed(() => invoiceIsCredit(props.invoice));
const shipmentLink = computed(() =>
	props.invoice.job_doctype === "Forwarding Job" && props.invoice.job_name
		? `/shipments/${encodeURIComponent(props.invoice.job_name)}`
		: null,
);
</script>
