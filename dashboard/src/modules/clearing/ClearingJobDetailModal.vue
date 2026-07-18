<template>
	<div class="sd-modal-backdrop" @click.self="$emit('close')">
		<div class="sd-modal-panel">
			<div class="sd-modal-header">
				<div>
					<div style="font-size: 12px; color: var(--sd-text-muted)">Clearing Job</div>
					<div style="font-size: 18px; font-weight: 700">{{ jobName }}</div>
				</div>
				<div class="sd-modal-header-actions">
					<DeskLink doctype="Clearing Job" :name="jobName" label="Edit in Desk" class="sd-modal-edit" />
					<button class="sd-modal-close" @click="$emit('close')"><X :size="16" stroke-width="2" /></button>
				</div>
			</div>

			<div class="sd-modal-body">
				<div v-if="loading" class="sd-state">Loading job details...</div>
				<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

				<template v-else-if="detail">
					<div class="sd-card">
						<div class="sd-card-title">
							<span>{{ detail.header.customer }}</span>
							<StatusBadge :status="detail.header.status" />
						</div>
						<div class="sd-grid sd-grid-2">
							<div class="sd-list">
								<li><span class="sd-muted">Reference</span><span>{{ detail.header.customer_reference || "–" }}</span></li>
								<li><span class="sd-muted">Direction</span><span>{{ detail.header.direction || "–" }}</span></li>
								<li><span class="sd-muted">Route</span><span>{{ detail.header.origin || "–" }} &rarr; {{ detail.header.destination || "–" }}</span></li>
								<li><span class="sd-muted">Shipping Line</span><span>{{ detail.header.shipping_line || "–" }}</span></li>
							</div>
							<div class="sd-list">
								<li><span class="sd-muted">BL Number</span><span>{{ detail.header.bl_number || "–" }}</span></li>
								<li><span class="sd-muted">BL Received / Confirmed</span><span>{{ detail.header.is_bl_received ? "Yes" : "No" }} / {{ detail.header.is_bl_confirmed ? "Yes" : "No" }}</span></li>
								<li><span class="sd-muted">Consignee</span><span>{{ detail.header.consignee || "–" }}</span></li>
								<li><span class="sd-muted">Last Update</span><span>{{ formatDate(detail.header.last_updated_on) }} · {{ detail.header.last_updated_by || "–" }}</span></li>
							</div>
						</div>
						<div v-if="detail.header.current_comment" class="cc-modal-note">
							<MessageSquare />
							<span><strong>Latest update:</strong> {{ detail.header.current_comment }}</span>
						</div>
					</div>

					<!-- Milestones -->
					<div class="sd-card">
						<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><ListChecks /></span>Clearing Progress</span></div>
						<div class="sd-stage-group">
							<div v-for="m in detail.milestones" :key="m.label" class="sd-stage-row">
								<span class="sd-stage-dot" :class="m.is_completed ? 'done' : 'pending'"><Check v-if="m.is_completed" :size="12" stroke-width="3" /></span>
								<span class="sd-stage-label">{{ m.label }}</span>
								<span class="sd-stage-date">{{ m.completed_on ? formatDate(m.completed_on) : "Pending" }}</span>
							</div>
						</div>
					</div>

					<!-- Cargo -->
					<div v-if="detail.cargo && detail.cargo.length" class="sd-card">
						<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><Package /></span>Cargo / Containers ({{ detail.cargo.length }})</span></div>
						<table class="sd-table">
							<thead><tr><th>Container / Item</th><th>Type</th><th>Loaded</th><th>Discharged</th><th>Gate Out</th><th>API Status</th></tr></thead>
							<tbody>
								<tr v-for="(row, i) in detail.cargo" :key="i">
									<td>{{ row.container_number }}</td>
									<td>{{ row.container_type || "–" }}</td>
									<td><TickCross :value="!!row.is_loaded" /></td>
									<td>{{ row.discharge_date ? formatDate(row.discharge_date) : "" }}<TickCross v-if="!row.discharge_date" :value="false" /></td>
									<td>{{ row.gate_out_full_date ? formatDate(row.gate_out_full_date) : "" }}<TickCross v-if="!row.gate_out_full_date" :value="false" /></td>
									<td>{{ row.api_container_status || "–" }}</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- Finance -->
					<div class="sd-card">
						<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><Wallet /></span>Finance</span></div>
						<table class="sd-table">
							<thead><tr><th></th><th class="sd-right">Revenue</th><th class="sd-right">Cost</th><th class="sd-right">Margin</th><th class="sd-right">Margin %</th></tr></thead>
							<tbody>
								<tr><td>Quoted</td><td class="sd-right">{{ formatMoney(detail.finance.quoted_revenue, detail.header.currency) }}</td><td class="sd-right">{{ formatMoney(detail.finance.quoted_cost, detail.header.currency) }}</td><td class="sd-right">{{ formatMoney(detail.finance.quoted_margin, detail.header.currency) }}</td><td class="sd-right">{{ detail.finance.quoted_margin_percent.toFixed(1) }}%</td></tr>
								<tr><td>Working</td><td class="sd-right">{{ formatMoney(detail.finance.working_revenue, detail.header.currency) }}</td><td class="sd-right">{{ formatMoney(detail.finance.working_cost, detail.header.currency) }}</td><td class="sd-right">{{ formatMoney(detail.finance.working_margin, detail.header.currency) }}</td><td class="sd-right">{{ detail.finance.working_margin_percent.toFixed(1) }}%</td></tr>
								<tr><td>Invoiced</td><td class="sd-right">{{ formatMoney(detail.finance.invoiced_revenue, detail.header.currency) }}</td><td class="sd-right">{{ formatMoney(detail.finance.invoiced_cost, detail.header.currency) }}</td><td class="sd-right">{{ formatMoney(detail.finance.invoiced_margin, detail.header.currency) }}</td><td class="sd-right">{{ detail.finance.invoiced_margin_percent.toFixed(1) }}%</td></tr>
							</tbody>
						</table>
					</div>

					<!-- Invoices -->
					<div v-if="detail.sales_invoices.length || detail.purchase_invoices.length" class="sd-card">
						<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><Receipt /></span>Invoices</span></div>
						<table class="sd-table" v-if="detail.sales_invoices.length">
							<thead><tr><th colspan="5" class="sd-muted" style="text-transform: none; font-weight: 600;">Sales Invoices</th></tr><tr><th>No.</th><th>Posting</th><th>Due</th><th class="sd-right">Amount</th><th class="sd-right">Balance</th></tr></thead>
							<tbody>
								<tr v-for="inv in detail.sales_invoices" :key="inv.name">
									<td><DeskLink doctype="Sales Invoice" :name="inv.name" plain /></td>
									<td>{{ formatDate(inv.posting_date) }}</td><td>{{ formatDate(inv.due_date) }}</td>
									<td class="sd-right">{{ formatMoney(inv.grand_total, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(inv.outstanding_amount, detail.header.currency) }}</td>
								</tr>
							</tbody>
						</table>
						<table class="sd-table" v-if="detail.purchase_invoices.length" style="margin-top: 10px;">
							<thead><tr><th colspan="5" class="sd-muted" style="text-transform: none; font-weight: 600;">Purchase Invoices</th></tr><tr><th>No.</th><th>Posting</th><th>Due</th><th class="sd-right">Amount</th><th class="sd-right">Balance</th></tr></thead>
							<tbody>
								<tr v-for="inv in detail.purchase_invoices" :key="inv.name">
									<td><DeskLink doctype="Purchase Invoice" :name="inv.name" plain /></td>
									<td>{{ formatDate(inv.posting_date) }}</td><td>{{ formatDate(inv.due_date) }}</td>
									<td class="sd-right">{{ formatMoney(inv.grand_total, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(inv.outstanding_amount, detail.header.currency) }}</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- Tracking -->
					<div v-if="detail.tracking.length" class="sd-card">
						<div class="sd-card-title"><span class="sd-card-title-main"><span class="sd-card-title-icon"><History /></span>Recent Tracking Updates</span></div>
						<ul class="sd-list">
							<li v-for="(t, idx) in detail.tracking" :key="idx" style="display: block;">
								<div style="display: flex; justify-content: space-between;">
									<strong style="font-size: 12px;">{{ t.source || t.updated_by || "Update" }}</strong>
									<span class="sd-muted" style="font-size: 12px;">{{ formatDateTime(t.updated_on) }}</span>
								</div>
								<div style="font-size: 13px; margin-top: 2px;">{{ t.comment }}</div>
							</li>
						</ul>
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { X, Check, Package, Wallet, Receipt, History, ListChecks, MessageSquare } from "@lucide/vue";
import { api } from "./api";
import { formatMoney, formatDate, formatDateTime } from "../../format";
import StatusBadge from "../../components/StatusBadge.vue";
import TickCross from "../../components/TickCross.vue";
import DeskLink from "../../components/DeskLink.vue";

const props = defineProps({ jobName: { type: String, required: true } });
defineEmits(["close"]);

const loading = ref(true);
const error = ref("");
const detail = ref(null);

async function load() {
	loading.value = true;
	error.value = "";
	try {
		detail.value = await api.getJobDetail(props.jobName);
	} catch (e) {
		error.value = e.message || "Failed to load job detail.";
	} finally {
		loading.value = false;
	}
}

onMounted(load);
</script>
