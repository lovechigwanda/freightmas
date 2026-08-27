<template>
	<router-link
		:to="`/invoices/${encodeURIComponent(invoice.name)}`"
		class="sd-invoice-list-card"
		:class="{
			'sd-invoice-list-card--overdue': invoice.is_overdue,
			'sd-invoice-list-card--credit': isCredit,
		}"
	>
		<div class="sd-invoice-list-card-row sd-invoice-list-card-row--primary">
			<div class="sd-invoice-list-card-identity">
				<component :is="listIcon" class="sd-invoice-list-card-mode" :size="16" stroke-width="2" />
				<span class="sd-invoice-list-card-primary">{{ primaryLabel }}</span>
				<span v-for="chip in contextChips" :key="chip.label" class="sd-invoice-list-card-chip">
					{{ chip.label }}
				</span>
				<span
					v-if="invoice.is_overdue"
					class="sd-invoice-list-card-chip sd-invoice-list-card-chip--warn"
				>
					Overdue
				</span>
			</div>
			<div class="sd-invoice-list-card-balance-col">
				<span class="sd-invoice-list-card-balance-label">{{ balanceLabel }}</span>
				<span class="sd-invoice-list-card-balance-value">{{ balanceAmount }}</span>
			</div>
		</div>

		<div class="sd-invoice-list-card-row sd-invoice-list-card-row--secondary">
			<p class="sd-invoice-list-card-meta">
				<span class="sd-invoice-list-card-meta-name">{{ secondaryMeta }}</span>
				<span
					v-if="due.display !== '–'"
					class="sd-invoice-list-card-due"
					:class="`sd-invoice-list-card-due--${due.urgency}`"
				>
					· {{ due.display }}
				</span>
			</p>
			<router-link
				v-if="shipmentLink"
				class="sd-table-link sd-invoice-list-card-shipment-link"
				:to="shipmentLink"
				@click.stop
			>
				View shipment
			</router-link>
		</div>
	</router-link>
</template>

<script setup>
import { computed } from "vue";
import {
	invoiceBalanceAmount,
	invoiceBalanceLabel,
	invoiceContextChips,
	invoiceDueLabel,
	invoiceIsCredit,
	invoiceListIcon,
	invoicePrimaryLabel,
	invoiceSecondaryMeta,
} from "../utils/invoiceList";

const props = defineProps({
	invoice: { type: Object, required: true },
});

const primaryLabel = computed(() => invoicePrimaryLabel(props.invoice));
const listIcon = computed(() => invoiceListIcon(props.invoice));
const contextChips = computed(() => invoiceContextChips(props.invoice));
const secondaryMeta = computed(() => invoiceSecondaryMeta(props.invoice));
const due = computed(() => invoiceDueLabel(props.invoice));
const balanceLabel = computed(() => invoiceBalanceLabel(props.invoice));
const balanceAmount = computed(() => invoiceBalanceAmount(props.invoice));
const isCredit = computed(() => invoiceIsCredit(props.invoice));
const shipmentLink = computed(() =>
	props.invoice.job_doctype === "Forwarding Job" && props.invoice.job_name
		? `/shipments/${encodeURIComponent(props.invoice.job_name)}`
		: null,
);
</script>
