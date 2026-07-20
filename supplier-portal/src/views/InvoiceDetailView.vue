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

			<div class="sd-card">
				<div class="sd-card-title"><span class="sd-card-title-main">Invoice Details</span></div>
				<ul class="sd-list">
					<li><span class="sd-muted">Job</span><span>{{ invoice.job_name || "–" }}</span></li>
					<li><span class="sd-muted">Posting Date</span><span>{{ formatDate(invoice.posting_date) }}</span></li>
					<li><span class="sd-muted">Due Date</span><span>{{ formatDate(invoice.due_date) }}</span></li>
					<li><span class="sd-muted">Amount</span><span>{{ formatMoney(invoice.grand_total) }}</span></li>
					<li><span class="sd-muted">Outstanding</span><span>{{ formatMoney(invoice.outstanding_amount) }}</span></li>
				</ul>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { api } from "../api/invoices";
import { formatDate, formatMoney } from "../format";
import StatusBadge from "../components/StatusBadge.vue";

const props = defineProps({ invoiceName: { type: String, required: true } });

const invoice = ref(null);
const loading = ref(true);
const error = ref("");

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
