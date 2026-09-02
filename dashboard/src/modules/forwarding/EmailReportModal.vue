<template>
	<div class="sd-modal-backdrop" @click.self="$emit('close')">
		<div class="sd-modal-panel erm-panel">
			<div class="sd-modal-header">
				<div style="font-size: 18px; font-weight: 700">Email {{ reportLabel }}</div>
				<button class="sd-modal-close" @click="$emit('close')"><X :size="16" stroke-width="2" /></button>
			</div>

			<div class="sd-modal-body">
				<div v-if="prefillWarning" class="cc-banner">{{ prefillWarning }}</div>
				<div v-if="error" class="sd-state erm-message" style="color: var(--sd-red)">{{ error }}</div>
				<div v-if="success" class="sd-state erm-message" style="color: var(--sd-green)">Email sent to {{ toEmail }}.</div>

				<label class="erm-field">
					<span>Customer</span>
					<div class="erm-customer-picker">
						<CustomerSingleSelect
							:model-value="selectedCustomer"
							@update:model-value="onCustomerChange"
						/>
					</div>
					<span class="erm-hint">Select a customer to load their tracking email addresses from Customer settings.</span>
				</label>
				<label class="erm-field">
					<span>To Email</span>
					<input v-model.trim="toEmail" type="email" placeholder="recipient@example.com" required />
				</label>
				<label class="erm-field">
					<span>CC Emails</span>
					<input v-model.trim="ccEmails" type="text" placeholder="comma separated" />
				</label>
				<label class="erm-field">
					<span>Subject</span>
					<input v-model.trim="subject" type="text" required />
				</label>
				<label class="erm-field">
					<span>Message</span>
					<textarea v-model="message" rows="6"></textarea>
				</label>

				<button type="button" class="sd-btn sd-btn-primary" :disabled="sending || !canSend" @click="send">
					<Mail :size="14" stroke-width="2" /> {{ sending ? "Sending..." : "Send Email" }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { X, Mail } from "@lucide/vue";
import { api, sendReportEmail } from "./api";
import { formatDate } from "../../format";
import CustomerSingleSelect from "../../components/CustomerSingleSelect.vue";

const props = defineProps({
	kind: { type: String, required: true },
	reportLabel: { type: String, required: true },
	customers: { type: Array, default: null },
	customer: { type: String, default: null },
});
defineEmits(["close"]);

const toEmail = ref("");
const ccEmails = ref("");
const subject = ref(`${props.reportLabel} - ${formatDate(new Date())}`);
const message = ref("Please find attached the requested tracking report.\n\nBest regards,");
const sending = ref(false);
const error = ref("");
const success = ref(false);
const prefillWarning = ref("");

const isShipmentReport = computed(
	() => props.kind === "shipmentTrackingReport" || props.kind === "shipmentTrackingReportExcel",
);

const selectedCustomer = ref(
	props.customer || (props.customers?.length === 1 ? props.customers[0] : null),
);

const needsCustomerSelection = computed(() => {
	if (isShipmentReport.value) {
		return !(selectedCustomer.value || props.customer);
	}
	if (props.customers?.length) {
		return false;
	}
	return !selectedCustomer.value;
});

const canSend = computed(() => Boolean(toEmail.value) && !needsCustomerSelection.value);

async function applyCustomerPrefill(customer) {
	prefillWarning.value = "";
	if (!customer) {
		toEmail.value = "";
		ccEmails.value = "";
		subject.value = `${props.reportLabel} - ${formatDate(new Date())}`;
		return;
	}
	try {
		const info = await api.getCustomerTrackingInfo(customer);
		if (!info) return;
		toEmail.value = info.tracking_email || info.email_id || "";
		ccEmails.value = info.tracking_cc_emails || "";
		if (info.customer_name) {
			subject.value = `${props.reportLabel} - ${info.customer_name}`;
		}
		if (info.tracking_email_enabled === 0) {
			prefillWarning.value = `Tracking emails are disabled for ${info.customer_name || customer} in Customer settings. You can still send manually.`;
		}
	} catch (e) {
		// Prefill is a convenience, not a hard requirement - fail silently.
	}
}

async function onCustomerChange(customer) {
	selectedCustomer.value = customer;
	await applyCustomerPrefill(customer);
}

onMounted(async () => {
	if (selectedCustomer.value) {
		await applyCustomerPrefill(selectedCustomer.value);
	}
});

async function send() {
	error.value = "";
	success.value = false;
	sending.value = true;
	try {
		const params = {
			to_email: toEmail.value,
			subject: subject.value,
			message: message.value,
			cc_emails: ccEmails.value,
		};
		if (isShipmentReport.value) {
			params.customer = selectedCustomer.value || props.customer;
		} else if (props.customers?.length) {
			params.customers = props.customers;
		} else if (selectedCustomer.value) {
			params.customers = [selectedCustomer.value];
		}
		await sendReportEmail(props.kind, params);
		success.value = true;
	} catch (e) {
		error.value = e.message || "Failed to send email.";
	} finally {
		sending.value = false;
	}
}
</script>

<style scoped>
.erm-panel {
	width: min(440px, 92vw);
}

.erm-message {
	padding: 10px 14px;
	text-align: left;
	font-size: 13px;
}

.erm-field {
	display: flex;
	flex-direction: column;
	gap: 6px;
	font-size: 13px;
	font-weight: 600;
	color: var(--sd-text);
}

.erm-customer-picker {
	width: 100%;
}

.erm-customer-picker :deep(.cfd-wrap) {
	display: block;
	width: 100%;
}

.erm-customer-picker :deep(.cfd-trigger) {
	width: 100%;
	justify-content: space-between;
}

.erm-hint {
	font-size: 12px;
	font-weight: 400;
	color: var(--sd-text-faint);
	line-height: 1.4;
}

.erm-field input,
.erm-field textarea {
	padding: 8px 12px;
	border: 1px solid var(--sd-border);
	border-radius: var(--sd-radius-sm);
	font-size: 13px;
	font-weight: 400;
	background: var(--sd-surface);
	color: var(--sd-text);
	font-family: inherit;
	transition: border-color 0.12s ease, box-shadow 0.12s ease;
}

.erm-field input:focus,
.erm-field textarea:focus {
	outline: none;
	border-color: var(--sd-accent);
	box-shadow: 0 0 0 3px var(--sd-accent-soft);
}

.erm-field textarea {
	resize: vertical;
}
</style>
