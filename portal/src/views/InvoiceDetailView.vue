<template>
	<div>
		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 4" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="invoice">
			<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
				<router-link to="/invoices" class="sd-table-link">&larr; Back to Invoices</router-link>
				<span style="font-weight: 600; font-size: 15px;">{{ invoice.name }}</span>
				<StatusBadge :status="invoice.status" />
			</div>

			<div class="sd-card" style="margin-bottom: 14px;">
				<div class="sd-card-title">
					<span class="sd-card-title-main">
						{{ invoice.job_name ? `${invoice.job_doctype}: ${invoice.job_name}` : "Invoice Details" }}
					</span>
				</div>
				<ul class="sd-list">
					<li><span class="sd-muted">Posted</span><span>{{ formatDate(invoice.posting_date) }}</span></li>
					<li><span class="sd-muted">Due Date</span><span>{{ formatDate(invoice.due_date) }}</span></li>
					<li><span class="sd-muted">Total</span><span>{{ formatMoney(invoice.grand_total) }}</span></li>
					<li><span class="sd-muted">Paid</span><span>{{ formatMoney(invoice.grand_total - invoice.outstanding_amount) }}</span></li>
					<li>
						<span class="sd-muted">Balance Due</span>
						<span style="font-weight: 700;">{{ formatMoney(invoice.outstanding_amount) }}</span>
					</li>
				</ul>
			</div>

			<div class="sd-card" style="margin-bottom: 14px;">
				<div class="sd-card-title"><span class="sd-card-title-main">Payment History</span></div>
				<ul class="sd-list" v-if="invoice.payment_history.length">
					<li v-for="(p, idx) in invoice.payment_history" :key="idx">
						<span class="cc-list-label">
							<span class="cc-list-text">{{ p.mode_of_payment || "Payment" }}<span v-if="p.reference_no"> &middot; Ref {{ p.reference_no }}</span></span>
						</span>
						<span style="display: flex; gap: 10px; align-items: center;">
							<span>{{ formatMoney(p.paid_amount) }}</span>
							<span class="sd-muted" style="font-size: 12px;">{{ formatDate(p.posting_date) }}</span>
						</span>
					</li>
				</ul>
				<EmptyState v-else :icon="Receipt" title="No payments recorded yet" />
			</div>

			<a class="sd-table-link" :href="pdfUrl" target="_blank" rel="noopener">
				<button class="sd-modal-edit" style="display: inline-flex; align-items: center; gap: 6px;">
					<Download :size="14" /> Download PDF
				</button>
			</a>
		</template>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Download, Receipt } from "@lucide/vue";
import { api } from "../api/invoices";
import { formatDate, formatMoney } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";

const props = defineProps({ invoiceName: { type: String, required: true } });

const invoice = ref(null);
const loading = ref(true);
const error = ref("");

const pdfUrl = computed(() => api.downloadPdfUrl(props.invoiceName));

async function load(invoiceName) {
	loading.value = true;
	error.value = "";
	try {
		invoice.value = await api.getInvoiceDetail(invoiceName);
	} catch (e) {
		error.value = e.message || "Failed to load this invoice.";
	} finally {
		loading.value = false;
	}
}

watch(() => props.invoiceName, (name) => name && load(name), { immediate: true });
</script>
