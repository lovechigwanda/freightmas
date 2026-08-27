<template>
	<div class="sd-card sd-dashboard-finance">
		<div class="sd-card-title">
			<span class="sd-card-title-main">Financial snapshot</span>
			<router-link to="/invoices" class="sd-table-link" style="font-size: 12px;">View invoices &rarr;</router-link>
		</div>

		<div class="sd-dashboard-finance-grid">
			<div class="sd-dashboard-finance-stat">
				<span class="sd-dashboard-finance-label">Outstanding</span>
				<span class="sd-dashboard-finance-value">{{ formatMoney(snapshot.outstanding_amount) }}</span>
			</div>
			<div class="sd-dashboard-finance-stat" :class="{ 'sd-dashboard-finance-stat--warn': snapshot.overdue_amount }">
				<span class="sd-dashboard-finance-label">Overdue</span>
				<span class="sd-dashboard-finance-value">{{ formatMoney(snapshot.overdue_amount) }}</span>
				<span v-if="snapshot.overdue_invoice_count" class="sd-muted sd-dashboard-finance-meta">
					{{ formatNumber(snapshot.overdue_invoice_count) }} invoice(s)
				</span>
			</div>
			<div class="sd-dashboard-finance-stat">
				<span class="sd-dashboard-finance-label">Paid (YTD)</span>
				<span class="sd-dashboard-finance-value">{{ formatMoney(snapshot.paid_ytd) }}</span>
			</div>
		</div>

		<div v-if="snapshot.next_due_invoice" class="sd-dashboard-finance-next">
			<span class="sd-muted">Next due:</span>
			<router-link
				class="sd-table-link"
				:to="`/invoices/${encodeURIComponent(snapshot.next_due_invoice.name)}`"
			>
				{{ snapshot.next_due_invoice.name }}
			</router-link>
			<span class="sd-muted">
				· {{ formatMoney(snapshot.next_due_invoice.outstanding_amount) }}
				· {{ formatDate(snapshot.next_due_invoice.due_date) }}
			</span>
		</div>
	</div>
</template>

<script setup>
import { formatDate, formatMoney, formatNumber } from "../format";

defineProps({
	snapshot: { type: Object, required: true },
});
</script>
