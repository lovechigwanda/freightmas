<template>
	<div>
		<div class="sd-card">
			<div class="sd-card-title" style="margin-bottom: 14px;">
				<span class="sd-card-title-main">Tracking Reports</span>
			</div>

			<div class="tr-table">
				<div class="tr-row">
					<div class="tr-name">Full Tracking Report</div>
					<div class="tr-filter">
						<CustomerFilterDropdown v-model="selectedCustomers" />
					</div>
					<div class="tr-action">
						<a class="sd-btn sd-btn-primary" :href="trackingReportHref" target="_blank" rel="noopener">
							<Download :size="14" stroke-width="2" /> Download Tracking Report
						</a>
						<button type="button" class="sd-btn" @click="openEmailModal('trackingReport')">
							<Mail :size="14" stroke-width="2" /> Email
						</button>
					</div>
				</div>

				<div class="tr-row">
					<div class="tr-name">Master Tracking Report</div>
					<div class="tr-filter">
						<CustomerFilterDropdown v-model="selectedMasterCustomers" />
					</div>
					<div class="tr-action">
						<a class="sd-btn sd-btn-primary" :href="masterTrackingReportHref" target="_blank" rel="noopener">
							<Download :size="14" stroke-width="2" /> Download Tracking Report
						</a>
						<button type="button" class="sd-btn" @click="openEmailModal('masterTrackingReport')">
							<Mail :size="14" stroke-width="2" /> Email
						</button>
					</div>
				</div>

				<div class="tr-row">
					<div class="tr-name">
						Shipment Tracking Report
						<span class="tr-badge-pdf">PDF</span>
					</div>
					<div class="tr-filter">
						<CustomerSingleSelect v-model="selectedTrackingCustomer" />
					</div>
					<div class="tr-action">
						<a
							class="sd-btn sd-btn-primary"
							:class="{ 'sd-btn-disabled': !selectedTrackingCustomer }"
							:href="shipmentTrackingReportHref"
							target="_blank" rel="noopener"
						>
							<Download :size="14" stroke-width="2" /> Download PDF Report
						</a>
						<button
							type="button"
							class="sd-btn"
							:disabled="!selectedTrackingCustomer"
							@click="openEmailModal('shipmentTrackingReport')"
						>
							<Mail :size="14" stroke-width="2" /> Email
						</button>
					</div>
				</div>

				<div class="tr-row">
					<div class="tr-name">
						Shipment Tracking Report
						<span class="tr-badge-xlsx">XLSX</span>
					</div>
					<div class="tr-filter">
						<CustomerSingleSelect v-model="selectedTrackingCustomerXlsx" />
					</div>
					<div class="tr-action">
						<a
							class="sd-btn sd-btn-primary"
							:class="{ 'sd-btn-disabled': !selectedTrackingCustomerXlsx }"
							:href="shipmentTrackingReportExcelHref"
							target="_blank" rel="noopener"
						>
							<Download :size="14" stroke-width="2" /> Download Excel Report
						</a>
						<button
							type="button"
							class="sd-btn"
							:disabled="!selectedTrackingCustomerXlsx"
							@click="openEmailModal('shipmentTrackingReportExcel')"
						>
							<Mail :size="14" stroke-width="2" /> Email
						</button>
					</div>
				</div>

				<div class="tr-row">
					<div class="tr-name">
						Simplified Tracking Report <span class="tr-soon">Soon</span>
					</div>
					<div class="tr-filter">
						<button type="button" class="cfd-trigger" disabled>Select Customers</button>
					</div>
					<div class="tr-action">
						<button type="button" class="sd-btn sd-btn-primary" disabled>
							<Download :size="14" stroke-width="2" /> Download Tracking Report
						</button>
					</div>
				</div>

				<div class="tr-row">
					<div class="tr-name">
						Per Job Tracking Report <span class="tr-soon">Soon</span>
					</div>
					<div class="tr-filter">
						<button type="button" class="cfd-trigger" disabled>Select Job</button>
					</div>
					<div class="tr-action">
						<button type="button" class="sd-btn sd-btn-primary" disabled>
							<Download :size="14" stroke-width="2" /> Download Tracking Report
						</button>
					</div>
				</div>
			</div>
		</div>

		<EmailReportModal
			v-if="emailModal"
			:key="emailModal.kind"
			:kind="emailModal.kind"
			:report-label="emailModal.reportLabel"
			:customers="emailModal.customers"
			:customer="emailModal.customer"
			@close="emailModal = null"
		/>
	</div>
</template>

<script setup>
import { ref, computed } from "vue";
import { Download, Mail } from "@lucide/vue";
import { exportUrl } from "./api";
import CustomerFilterDropdown from "../../components/CustomerFilterDropdown.vue";
import CustomerSingleSelect from "../../components/CustomerSingleSelect.vue";
import EmailReportModal from "./EmailReportModal.vue";

const selectedCustomers = ref([]);
const selectedMasterCustomers = ref([]);
// Single customer name (or null) - this report only ever targets one customer,
// so the param below is `customer` (singular), not `customers` (array). The PDF
// and XLSX rows each keep their own independent selection (not shared state).
const selectedTrackingCustomer = ref(null);
const selectedTrackingCustomerXlsx = ref(null);

const emailModal = ref(null);
const rowMeta = {
	trackingReport: { reportLabel: "Full Tracking Report" },
	masterTrackingReport: { reportLabel: "Master Tracking Report" },
	shipmentTrackingReport: { reportLabel: "Shipment Tracking Report (PDF)" },
	shipmentTrackingReportExcel: { reportLabel: "Shipment Tracking Report (Excel)" },
};

function openEmailModal(kind) {
	const base = { kind, reportLabel: rowMeta[kind].reportLabel };
	if (kind === "trackingReport") emailModal.value = { ...base, customers: [...selectedCustomers.value] };
	else if (kind === "masterTrackingReport") emailModal.value = { ...base, customers: [...selectedMasterCustomers.value] };
	else if (kind === "shipmentTrackingReport") emailModal.value = { ...base, customer: selectedTrackingCustomer.value };
	else if (kind === "shipmentTrackingReportExcel") emailModal.value = { ...base, customer: selectedTrackingCustomerXlsx.value };
}

const trackingReportHref = computed(() =>
	exportUrl("trackingReport", { customers: selectedCustomers.value })
);
const masterTrackingReportHref = computed(() =>
	exportUrl("masterTrackingReport", { customers: selectedMasterCustomers.value })
);
const shipmentTrackingReportHref = computed(() =>
	exportUrl("shipmentTrackingReport", { customer: selectedTrackingCustomer.value })
);
const shipmentTrackingReportExcelHref = computed(() =>
	exportUrl("shipmentTrackingReportExcel", { customer: selectedTrackingCustomerXlsx.value })
);
</script>

<style scoped>
.tr-table {
	display: flex;
	flex-direction: column;
}

.tr-row {
	display: grid;
	grid-template-columns: 220px 200px 1fr;
	align-items: center;
	gap: 16px;
	padding: 12px 0;
	border-top: 1px solid var(--sd-border-soft);
}

.tr-row:first-child {
	border-top: none;
}

.tr-name {
	font-size: 14px;
	font-weight: 600;
	color: var(--sd-text);
	display: flex;
	align-items: center;
	gap: 8px;
}

.tr-action {
	display: flex;
	align-items: center;
	gap: 8px;
}

.tr-soon {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	color: var(--sd-text-faint);
	background: var(--sd-surface-alt);
	border: 1px solid var(--sd-border);
	padding: 2px 6px;
	border-radius: 999px;
}

/* Same pill as .tr-soon, brand-tinted (the .cc-banner recipe from style.css). */
.tr-badge-pdf {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	color: var(--sd-accent-soft-text);
	background: var(--sd-accent-soft);
	border: 1px solid #dfe2fb;
	padding: 2px 6px;
	border-radius: 999px;
}

/* Same pill, green-tinted for the Excel row. */
.tr-badge-xlsx {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	color: #186429;
	background: #e5f3ea;
	border: 1px solid #cdeada;
	padding: 2px 6px;
	border-radius: 999px;
}

.tr-filter .cfd-trigger {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 8px 12px;
	border: 1px solid var(--sd-border);
	border-radius: var(--sd-radius-sm);
	background: var(--sd-surface);
	color: var(--sd-text-faint);
	font-size: 13px;
	font-family: inherit;
}

.tr-filter button[disabled],
.tr-action button[disabled] {
	opacity: 0.5;
	cursor: not-allowed;
}
</style>
