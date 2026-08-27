<template>
	<div class="sd-card sd-invoices-card" :class="{ 'sd-invoices-card--compact': compactEmpty && !hasInvoices && !loading && !error }">
		<div class="sd-card-title"><span class="sd-card-title-main">Invoices</span></div>

		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 3" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red); padding: 20px 0;">{{ error }}</div>
		<div v-else>
			<template v-if="hasInvoices">
				<ul class="sd-invoices-list">
					<li v-for="inv in invoices" :key="inv.name" class="sd-invoices-list-item">
						<div class="sd-invoices-list-main">
							<router-link
								class="sd-invoices-list-label"
								:to="`/invoices/${encodeURIComponent(inv.name)}`"
							>
								{{ inv.name }}
							</router-link>
							<div class="sd-muted sd-invoices-list-meta">
								Due {{ formatDate(inv.due_date) }} · {{ formatMoney(inv.grand_total) }}
							</div>
						</div>
						<div class="sd-invoices-list-actions">
							<StatusBadge :status="inv.status" />
							<a
								class="sd-invoices-download"
								:href="pdfUrl(inv.name)"
								target="_blank"
								rel="noopener"
							>
								PDF
							</a>
						</div>
					</li>
				</ul>
			</template>
			<p v-else-if="compactEmpty" class="sd-invoices-empty-compact sd-muted">
				No invoices for this shipment yet.
			</p>
			<EmptyState
				v-else
				:icon="Receipt"
				title="No invoices yet"
				sub="Invoices linked to this shipment will appear here."
			/>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Receipt } from "@lucide/vue";
import { api } from "../api/invoices";
import { formatDate, formatMoney } from "../format";
import EmptyState from "./EmptyState.vue";
import StatusBadge from "./StatusBadge.vue";

const props = defineProps({
	invoices: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
	error: { type: String, default: "" },
	compactEmpty: { type: Boolean, default: false },
});

const hasInvoices = computed(() => (props.invoices || []).length > 0);

function pdfUrl(invoiceName) {
	return api.downloadPdfUrl(invoiceName);
}
</script>
