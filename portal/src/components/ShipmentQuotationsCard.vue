<template>
	<div class="sd-card sd-invoices-card" :class="{ 'sd-invoices-card--compact': compactEmpty && !hasQuotations && !loading && !error }">
		<div class="sd-card-title"><span class="sd-card-title-main">Quotations</span></div>

		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 3" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red); padding: 20px 0;">{{ error }}</div>
		<div v-else>
			<template v-if="hasQuotations">
				<ul class="sd-invoices-list">
					<li v-for="quote in quotations" :key="quote.name" class="sd-invoices-list-item">
						<div class="sd-invoices-list-main">
							<router-link
								class="sd-invoices-list-label"
								:to="`/quotations/${encodeURIComponent(quote.name)}`"
							>
								{{ quote.name }}
							</router-link>
							<div class="sd-muted sd-invoices-list-meta">
								{{ formatDate(quote.transaction_date) }} · {{ formatMoney(quote.grand_total) }}
							</div>
						</div>
						<div class="sd-invoices-list-actions">
							<StatusBadge :status="quote.client_status || quote.workflow_state" />
							<a
								class="sd-invoices-download"
								:href="pdfUrl(quote.name)"
								rel="noopener"
							>
								Download
							</a>
						</div>
					</li>
				</ul>
			</template>
			<p v-else-if="compactEmpty" class="sd-invoices-empty-compact sd-muted">
				No approved quotations linked to this shipment yet.
			</p>
			<EmptyState
				v-else
				:icon="FileText"
				title="No quotations yet"
				sub="Approved quotations linked to this shipment will appear here."
			/>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { FileText } from "@lucide/vue";
import { api } from "../api/quotations";
import { formatDate, formatMoney } from "../format";
import EmptyState from "./EmptyState.vue";
import StatusBadge from "./StatusBadge.vue";

const props = defineProps({
	quotations: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
	error: { type: String, default: "" },
	compactEmpty: { type: Boolean, default: false },
});

const hasQuotations = computed(() => (props.quotations || []).length > 0);

function pdfUrl(quotationName) {
	return api.downloadPdfUrl(quotationName);
}
</script>
