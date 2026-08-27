<template>
	<div class="sd-card sd-invoice-account-header">
		<div class="sd-invoice-account-header-main">
			<div class="sd-invoice-account-header-stat">
				<span class="sd-invoice-account-header-label">Outstanding</span>
				<span class="sd-invoice-account-header-value">{{ formatMoney(summary.outstanding_amount) }}</span>
			</div>
			<div
				class="sd-invoice-account-header-stat"
				:class="{ 'sd-invoice-account-header-stat--warn': summary.overdue_amount }"
			>
				<span class="sd-invoice-account-header-label">Overdue</span>
				<span class="sd-invoice-account-header-value">{{ formatMoney(summary.overdue_amount) }}</span>
			</div>
			<div class="sd-invoice-account-header-stat">
				<span class="sd-invoice-account-header-label">Open invoices</span>
				<span class="sd-invoice-account-header-value">{{ formatNumber(summary.open_invoice_count) }}</span>
			</div>
			<div class="sd-invoice-account-header-stat">
				<span class="sd-invoice-account-header-label">Paid (YTD)</span>
				<span class="sd-invoice-account-header-value">{{ formatMoney(summary.paid_ytd) }}</span>
			</div>
		</div>

		<div class="sd-invoice-account-header-actions">
			<a class="sd-table-link sd-invoices-export-link" :href="pdfUrl" rel="noopener">
				<Download :size="14" style="vertical-align: -2px;" /> Statement PDF
			</a>
			<a class="sd-table-link sd-invoices-export-link" :href="excelUrl" rel="noopener">
				<Download :size="14" style="vertical-align: -2px;" /> Statement Excel
			</a>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Download } from "@lucide/vue";
import { formatMoney, formatNumber } from "../format";

const props = defineProps({
	summary: { type: Object, required: true },
	statementUrlBuilder: { type: Function, required: true },
});

const pdfUrl = computed(() => props.statementUrlBuilder({ format: "pdf" }));
const excelUrl = computed(() => props.statementUrlBuilder({ format: "excel" }));
</script>
