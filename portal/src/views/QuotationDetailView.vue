<template>
	<div>
		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 4" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="quotation">
			<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap;">
				<router-link to="/quotations" class="sd-table-link">&larr; Back to Quotations</router-link>
				<span style="font-weight: 600; font-size: 15px;">{{ quotation.name }}</span>
				<StatusBadge :status="quotation.client_status || quotation.workflow_state" />
			</div>

			<div
				v-if="quotation.can_approve"
				class="sd-card"
				style="margin-bottom: 14px; padding: 16px 18px; border-left: 3px solid var(--sd-amber);"
			>
				<div style="font-weight: 600; margin-bottom: 8px;">This quotation is awaiting your approval</div>
				<p v-if="quotation.is_expired" class="sd-muted" style="color: var(--sd-red); margin-bottom: 10px;">
					This quotation has expired and can no longer be accepted.
				</p>
				<p v-else-if="expiryWarning" class="sd-muted" style="margin-bottom: 10px;">{{ expiryWarning }}</p>
				<div style="display: flex; gap: 10px; flex-wrap: wrap;">
					<button
						class="sd-modal-edit"
						:disabled="actionLoading || quotation.is_expired"
						@click="openApproveConfirm"
					>
						Approve quotation
					</button>
					<button
						class="sd-table-link"
						style="padding: 8px 14px;"
						:disabled="actionLoading || quotation.is_expired"
						@click="showRejectDialog = true"
					>
						Decline
					</button>
				</div>
			</div>

			<div class="sd-card sd-invoice-detail-summary" style="margin-bottom: 14px;">
				<div class="sd-invoice-detail-summary-main">
					<span class="sd-muted">Grand total</span>
					<span class="sd-invoice-detail-summary-balance">{{ formatMoney(quotation.grand_total) }}</span>
				</div>
				<ul class="sd-list">
					<li><span class="sd-muted">Quoted</span><span>{{ formatDate(quotation.transaction_date) }}</span></li>
					<li><span class="sd-muted">Valid until</span><span>{{ formatDate(quotation.valid_till) }}</span></li>
					<li v-if="quotation.customer_reference">
						<span class="sd-muted">Your reference</span><span>{{ quotation.customer_reference }}</span>
					</li>
					<li v-if="quotation.job_type">
						<span class="sd-muted">Service type</span><span>{{ quotation.job_type }}</span>
					</li>
				</ul>
			</div>

			<div v-if="routeSummary" class="sd-card" style="margin-bottom: 14px;">
				<div class="sd-card-title"><span class="sd-card-title-main">Route & service</span></div>
				<ul class="sd-list">
					<li v-if="quotation.origin_port">
						<span class="sd-muted">Origin</span><span>{{ quotation.origin_port }}</span>
					</li>
					<li v-if="quotation.port_of_discharge">
						<span class="sd-muted">Port of discharge</span><span>{{ quotation.port_of_discharge }}</span>
					</li>
					<li v-if="quotation.destination_port">
						<span class="sd-muted">Destination</span><span>{{ quotation.destination_port }}</span>
					</li>
					<li v-if="quotation.job_description">
						<span class="sd-muted">Description</span><span>{{ quotation.job_description }}</span>
					</li>
				</ul>
			</div>

			<div v-if="shipmentLink" class="sd-card" style="margin-bottom: 14px;">
				<div class="sd-card-title"><span class="sd-card-title-main">Linked shipment</span></div>
				<ul class="sd-list">
					<li>
						<span class="sd-muted">Reference</span>
						<span>{{ quotation.job_customer_reference || quotation.job_name }}</span>
					</li>
					<li>
						<span class="sd-muted">Job</span>
						<router-link class="sd-table-link" :to="shipmentLink">{{ quotation.job_name }}</router-link>
					</li>
				</ul>
			</div>

			<div class="sd-card" style="margin-bottom: 14px;">
				<div class="sd-card-title"><span class="sd-card-title-main">Line items</span></div>
				<table class="sd-table" v-if="quotation.items?.length">
					<thead>
						<tr>
							<th>Description</th>
							<th style="text-align: right;">Qty</th>
							<th style="text-align: right;">Rate</th>
							<th style="text-align: right;">Amount</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="item in quotation.items" :key="item.idx">
							<td>{{ item.description || item.item_name || item.item_code }}</td>
							<td style="text-align: right;">{{ item.qty }}</td>
							<td style="text-align: right;">{{ formatMoney(item.rate) }}</td>
							<td style="text-align: right;">{{ formatMoney(item.amount) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="FileText" title="No line items" />
			</div>

			<div v-if="quotation.payment_terms_template" class="sd-card" style="margin-bottom: 14px;">
				<div class="sd-card-title"><span class="sd-card-title-main">Payment terms</span></div>
				<p>{{ quotation.payment_terms_template }}</p>
			</div>

			<a class="sd-table-link" :href="pdfUrl" rel="noopener">
				<button class="sd-modal-edit" style="display: inline-flex; align-items: center; gap: 6px;">
					<Download :size="14" /> Download PDF
				</button>
			</a>

			<div v-if="actionMessage" class="sd-muted" style="margin-top: 12px;">{{ actionMessage }}</div>
		</template>

		<div v-if="showApproveConfirm" class="sd-modal-backdrop" @click.self="showApproveConfirm = false">
			<div class="sd-modal">
				<h3 style="margin: 0 0 10px;">Approve this quotation?</h3>
				<p class="sd-muted">You are confirming acceptance of {{ quotation?.name }} for {{ formatMoney(quotation?.grand_total) }}.</p>
				<div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px;">
					<button class="sd-table-link" @click="showApproveConfirm = false">Cancel</button>
					<button class="sd-modal-edit" :disabled="actionLoading" @click="confirmApprove">Approve</button>
				</div>
			</div>
		</div>

		<div v-if="showRejectDialog" class="sd-modal-backdrop" @click.self="showRejectDialog = false">
			<div class="sd-modal">
				<h3 style="margin: 0 0 10px;">Decline this quotation?</h3>
				<p class="sd-muted" style="margin-bottom: 10px;">Optionally tell us why you are declining.</p>
				<textarea
					v-model="rejectReason"
					rows="3"
					style="width: 100%; box-sizing: border-box;"
					placeholder="Reason (optional)"
				></textarea>
				<div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px;">
					<button class="sd-table-link" @click="showRejectDialog = false">Cancel</button>
					<button class="sd-modal-edit" :disabled="actionLoading" @click="confirmReject">Decline</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Download, FileText } from "@lucide/vue";
import { api } from "../api/quotations";
import { formatDate, formatMoney } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";

const props = defineProps({ quotationName: { type: String, required: true } });

const quotation = ref(null);
const loading = ref(true);
const error = ref("");
const actionLoading = ref(false);
const actionMessage = ref("");
const showApproveConfirm = ref(false);
const showRejectDialog = ref(false);
const rejectReason = ref("");

const pdfUrl = computed(() => api.downloadPdfUrl(props.quotationName));
const shipmentLink = computed(() =>
	quotation.value?.job_name ? `/shipments/${encodeURIComponent(quotation.value.job_name)}` : null,
);
const routeSummary = computed(
	() =>
		quotation.value?.origin_port ||
		quotation.value?.port_of_discharge ||
		quotation.value?.destination_port ||
		quotation.value?.job_description,
);

const expiryWarning = computed(() => {
	if (!quotation.value?.valid_till || quotation.value.is_expired) return "";
	const valid = new Date(quotation.value.valid_till);
	const now = new Date();
	const days = Math.ceil((valid - now) / (1000 * 60 * 60 * 24));
	if (days <= 7 && days >= 0) {
		return `This quotation expires in ${days} day(s).`;
	}
	return "";
});

async function load(quotationName) {
	loading.value = true;
	error.value = "";
	actionMessage.value = "";
	try {
		quotation.value = await api.getQuotationDetail(quotationName);
	} catch (e) {
		error.value = e.message || "Failed to load this quotation.";
	} finally {
		loading.value = false;
	}
}

function openApproveConfirm() {
	showApproveConfirm.value = true;
}

async function confirmApprove() {
	actionLoading.value = true;
	try {
		quotation.value = await api.approveQuotation(props.quotationName);
		actionMessage.value = "Quotation approved successfully.";
		showApproveConfirm.value = false;
	} catch (e) {
		actionMessage.value = e.message || "Failed to approve quotation.";
	} finally {
		actionLoading.value = false;
	}
}

async function confirmReject() {
	actionLoading.value = true;
	try {
		quotation.value = await api.rejectQuotation(
			props.quotationName,
			rejectReason.value.trim() || undefined,
		);
		actionMessage.value = "Quotation declined.";
		showRejectDialog.value = false;
		rejectReason.value = "";
	} catch (e) {
		actionMessage.value = e.message || "Failed to decline quotation.";
	} finally {
		actionLoading.value = false;
	}
}

watch(() => props.quotationName, (name) => name && load(name), { immediate: true });
</script>
