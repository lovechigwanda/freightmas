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

				<button type="button" class="sd-btn sd-btn-primary" :disabled="sending || !toEmail" @click="send">
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

const props = defineProps({
	kind: { type: String, required: true },
	reportLabel: { type: String, required: true },
	customers: { type: Array, default: null },
	customer: { type: String, default: null },
});
const emit = defineEmits(["close"]);

const toEmail = ref("");
const ccEmails = ref("");
const subject = ref(`${props.reportLabel} - ${formatDate(new Date())}`);
const message = ref("Please find attached the requested tracking report.\n\nKindly quote your job reference in any reply.\n\nYours faithfully,");
const sending = ref(false);
const error = ref("");
const success = ref(false);
const prefillWarning = ref("");

// Single-customer scope: Shipment rows always pass `customer`; Full/Master
// rows only prefill when their multi-select currently holds exactly one.
const singleCustomer = computed(() => props.customer || (props.customers?.length === 1 ? props.customers[0] : null));

onMounted(async () => {
	if (!singleCustomer.value) return;
	try {
		const info = await api.getCustomerTrackingInfo(singleCustomer.value);
		if (!info) return;
		toEmail.value = info.tracking_email || info.email_id || "";
		ccEmails.value = info.tracking_cc_emails || "";
		if (info.customer_name) subject.value = `${props.reportLabel} - ${info.customer_name}`;
		if (info.tracking_email_enabled === 0) {
			prefillWarning.value = `Tracking emails are disabled for ${info.customer_name || singleCustomer.value} in Customer settings. You can still send manually.`;
		}
	} catch (e) {
		// Prefill is a convenience, not a hard requirement - fail silently.
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
		if (props.customer) params.customer = props.customer;
		if (props.customers) params.customers = props.customers;
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
