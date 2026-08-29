<template>
	<div class="sd-card sd-dashboard-attention">
		<div class="sd-card-title">
			<span class="sd-card-title-main">Needs your attention</span>
		</div>

		<ul v-if="items.length" class="sd-dashboard-attention-list">
			<li v-for="(item, idx) in items" :key="`${item.type}-${idx}`" class="sd-dashboard-attention-item">
				<div class="sd-dashboard-attention-icon" :class="`sd-dashboard-attention-icon--${item.type}`">
					<component :is="iconFor(item.type)" :size="16" stroke-width="2" />
				</div>
				<div class="sd-dashboard-attention-body">
					<div class="sd-dashboard-attention-title">{{ item.title }}</div>
					<div class="sd-muted sd-dashboard-attention-subtitle">{{ item.subtitle }}</div>
				</div>
				<a
					v-if="item.type === 'new_document'"
					class="sd-table-link sd-dashboard-attention-action"
					:href="downloadDocumentUrl(item.document_job_name, item.document_name)"
					rel="noopener"
				>
					Download
				</a>
				<router-link
					v-else-if="item.type === 'overdue_invoice'"
					class="sd-table-link sd-dashboard-attention-action"
					:to="`/invoices/${encodeURIComponent(item.invoice_name)}`"
				>
					View invoice
				</router-link>
				<router-link
					v-else-if="item.type === 'pending_quotation'"
					class="sd-table-link sd-dashboard-attention-action"
					:to="`/quotations/${encodeURIComponent(item.quotation_name)}`"
				>
					Review quote
				</router-link>
				<router-link
					v-else
					class="sd-table-link sd-dashboard-attention-action"
					:to="`/shipments/${encodeURIComponent(item.job_name)}`"
				>
					View shipment
				</router-link>
			</li>
		</ul>
		<EmptyState
			v-else
			:icon="CheckCircle2"
			title="All clear"
			sub="Nothing needs your attention right now."
		/>
	</div>
</template>

<script setup>
import { AlertTriangle, CheckCircle2, FileText, Package, Receipt } from "@lucide/vue";
import EmptyState from "./EmptyState.vue";
import { api as documentsApi } from "../api/documents";

defineProps({
	items: { type: Array, default: () => [] },
});

const ICONS = {
	delayed_shipment: AlertTriangle,
	arriving_soon: Package,
	overdue_invoice: Receipt,
	new_document: FileText,
	pending_quotation: FileText,
};

function iconFor(type) {
	return ICONS[type] || AlertTriangle;
}

function downloadDocumentUrl(jobName, checklistRow) {
	return documentsApi.downloadDocumentUrl(jobName, checklistRow);
}
</script>
