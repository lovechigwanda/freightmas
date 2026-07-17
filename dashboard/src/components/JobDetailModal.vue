<template>
	<div class="sd-modal-backdrop" @click.self="$emit('close')">
		<div class="sd-modal-panel">
			<div class="sd-modal-header">
				<div>
					<div style="font-size: 12px; color: var(--sd-text-muted)">Forwarding Job</div>
					<div style="font-size: 18px; font-weight: 700">{{ jobName }}</div>
				</div>
				<button class="sd-modal-close" @click="$emit('close')">&#10005;</button>
			</div>

			<div class="sd-modal-body">
				<div v-if="loading" class="sd-state">Loading job details...</div>
				<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

				<template v-else-if="detail">
					<!-- Header -->
					<div class="sd-card">
						<div class="sd-card-title">
							<span>{{ detail.header.customer }}</span>
							<StatusBadge :status="detail.header.status" />
						</div>
						<div class="sd-grid sd-grid-2">
							<div class="sd-list">
								<li><span class="sd-muted">Reference</span><span>{{ detail.header.customer_reference || "\u2013" }}</span></li>
								<li><span class="sd-muted">Direction / Mode</span><span>{{ detail.header.direction }} &middot; {{ detail.header.shipment_mode }}</span></li>
								<li><span class="sd-muted">Route</span><span>{{ detail.header.port_of_loading }} &rarr; {{ detail.header.port_of_discharge }} &rarr; {{ detail.header.destination }}</span></li>
								<li><span class="sd-muted">Vessel / Flight</span><span>{{ detail.header.vessel_flight_no || "\u2013" }}</span></li>
							</div>
							<div class="sd-list">
								<li><span class="sd-muted">BL Number</span><span>{{ detail.header.bl_number || "\u2013" }}</span></li>
								<li><span class="sd-muted">BL Received / Confirmed</span><span>{{ detail.header.is_bl_received ? "Yes" : "No" }} / {{ detail.header.is_bl_confirmed ? "Yes" : "No" }}</span></li>
								<li><span class="sd-muted">Consignee</span><span>{{ detail.header.consignee || "\u2013" }}</span></li>
								<li><span class="sd-muted">Last Update</span><span>{{ formatDate(detail.header.last_updated_on) }} &middot; {{ detail.header.last_updated_by || "\u2013" }}</span></li>
							</div>
						</div>
						<div v-if="detail.header.current_comment" style="margin-top: 12px; padding: 10px 12px; background: #fef3e0; border-radius: 8px; font-size: 13px;">
							<strong>Latest update:</strong> {{ detail.header.current_comment }}
						</div>
					</div>

					<!-- Stage tracker -->
					<div class="sd-card">
						<div class="sd-card-title">Shipment Progress</div>

						<div class="sd-stage-group">
							<div class="sd-stage-group-title">Shipment</div>
							<div
								v-for="stage in shipmentStages"
								:key="stage.label"
								class="sd-stage-row"
							>
								<span class="sd-stage-dot" :class="stage.done ? 'done' : 'pending'">{{ stage.done ? "\u2713" : "" }}</span>
								<span class="sd-stage-label">{{ stage.label }}</span>
								<span class="sd-stage-date">{{ stage.date ? formatDate(stage.date) : "Pending" }}</span>
							</div>
						</div>

						<div v-for="group in detail.milestone_stages" :key="group.group" class="sd-stage-group">
							<div class="sd-stage-group-title">{{ group.group }}</div>
							<div v-for="m in group.milestones" :key="m.label" class="sd-stage-row">
								<span class="sd-stage-dot" :class="m.is_completed ? 'done' : 'pending'">{{ m.is_completed ? "\u2713" : "" }}</span>
								<span class="sd-stage-label">{{ m.label }}</span>
								<span class="sd-stage-date">{{ m.completed_on ? formatDate(m.completed_on) : "Pending" }}</span>
							</div>
						</div>
					</div>

					<!-- Cargo / containers -->
					<div v-if="detail.cargo && detail.cargo.length" class="sd-card">
						<div class="sd-card-title">Cargo / Containers ({{ detail.cargo.length }})</div>
						<table class="sd-table">
							<thead>
								<tr>
									<th>Container / Item</th>
									<th>Type</th>
									<th>Booked</th>
									<th>Loaded</th>
									<th>Discharged</th>
									<th>Gate Out</th>
									<th>Returned</th>
									<th>API Status</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in detail.cargo" :key="row.name">
									<td>{{ row.container_number }}</td>
									<td>{{ row.container_type || "\u2013" }}</td>
									<td>{{ tickCross(row.is_booked) }}</td>
									<td>{{ tickCross(row.is_loaded) }}</td>
									<td>{{ row.discharge_date ? formatDate(row.discharge_date) : tickCross(false) }}</td>
									<td>{{ row.gate_out_date ? formatDate(row.gate_out_date) : tickCross(false) }}</td>
									<td>{{ row.to_be_returned ? tickCross(row.is_returned) : "\u2013" }}</td>
									<td>{{ row.api_container_status || "\u2013" }}</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- DND -->
					<div v-if="detail.dnd_totals && detail.dnd_totals.total_est_dnd_storage_cost" class="sd-card">
						<div class="sd-card-title">DND &amp; Storage Exposure</div>
						<div class="sd-grid sd-grid-kpi" style="margin-bottom: 12px;">
							<KpiCard label="DND Cost" :value="formatMoney(detail.dnd_totals.total_est_dnd_cost, detail.header.currency)" />
							<KpiCard label="Storage Cost" :value="formatMoney(detail.dnd_totals.total_est_storage_cost, detail.header.currency)" />
							<KpiCard label="Total Exposure" :value="formatMoney(detail.dnd_totals.total_est_dnd_storage_cost, detail.header.currency)" tone="warn" />
						</div>
						<table class="sd-table" v-if="detail.dnd_rows.length">
							<thead>
								<tr>
									<th>Container</th>
									<th>DND Days</th>
									<th>DND Cost</th>
									<th>Storage Days</th>
									<th>Storage Cost</th>
									<th class="sd-right">Total</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in detail.dnd_rows" :key="row.container_number">
									<td>{{ row.container_number }}</td>
									<td>{{ row.chargeable_dnd_days }} / {{ row.total_dnd_days }}</td>
									<td>{{ formatMoney(row.estimated_dnd_cost, detail.header.currency) }}</td>
									<td>{{ row.chargeable_storage_days }} / {{ row.total_storage_days }}</td>
									<td>{{ formatMoney(row.estimated_storage_cost, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(row.total_container_cost, detail.header.currency) }}</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- Finance -->
					<div class="sd-card">
						<div class="sd-card-title">Finance</div>
						<table class="sd-table">
							<thead>
								<tr>
									<th></th>
									<th class="sd-right">Revenue</th>
									<th class="sd-right">Cost</th>
									<th class="sd-right">Margin</th>
									<th class="sd-right">Margin %</th>
								</tr>
							</thead>
							<tbody>
								<tr>
									<td>Quoted</td>
									<td class="sd-right">{{ formatMoney(detail.finance.quoted_revenue, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(detail.finance.quoted_cost, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(detail.finance.quoted_margin, detail.header.currency) }}</td>
									<td class="sd-right">{{ detail.finance.quoted_margin_percent.toFixed(1) }}%</td>
								</tr>
								<tr>
									<td>Working</td>
									<td class="sd-right">{{ formatMoney(detail.finance.working_revenue, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(detail.finance.working_cost, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(detail.finance.working_margin, detail.header.currency) }}</td>
									<td class="sd-right">{{ detail.finance.working_margin_percent.toFixed(1) }}%</td>
								</tr>
								<tr>
									<td>Invoiced</td>
									<td class="sd-right">{{ formatMoney(detail.finance.invoiced_revenue, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(detail.finance.invoiced_cost, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(detail.finance.invoiced_margin, detail.header.currency) }}</td>
									<td class="sd-right">{{ detail.finance.invoiced_margin_percent.toFixed(1) }}%</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- Invoices -->
					<div v-if="detail.sales_invoices.length || detail.purchase_invoices.length" class="sd-card">
						<div class="sd-card-title">Invoices</div>
						<table class="sd-table" v-if="detail.sales_invoices.length">
							<thead>
								<tr><th colspan="5" class="sd-muted" style="text-transform: none; font-weight: 600;">Sales Invoices</th></tr>
								<tr>
									<th>No.</th><th>Posting Date</th><th>Due Date</th><th class="sd-right">Amount</th><th class="sd-right">Balance</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="inv in detail.sales_invoices" :key="inv.name">
									<td>{{ inv.name }}</td>
									<td>{{ formatDate(inv.posting_date) }}</td>
									<td>{{ formatDate(inv.due_date) }}</td>
									<td class="sd-right">{{ formatMoney(inv.grand_total, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(inv.outstanding_amount, detail.header.currency) }}</td>
								</tr>
							</tbody>
						</table>
						<table class="sd-table" v-if="detail.purchase_invoices.length" style="margin-top: 10px;">
							<thead>
								<tr><th colspan="5" class="sd-muted" style="text-transform: none; font-weight: 600;">Purchase Invoices</th></tr>
								<tr>
									<th>No.</th><th>Posting Date</th><th>Due Date</th><th class="sd-right">Amount</th><th class="sd-right">Balance</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="inv in detail.purchase_invoices" :key="inv.name">
									<td>{{ inv.name }}</td>
									<td>{{ formatDate(inv.posting_date) }}</td>
									<td>{{ formatDate(inv.due_date) }}</td>
									<td class="sd-right">{{ formatMoney(inv.grand_total, detail.header.currency) }}</td>
									<td class="sd-right">{{ formatMoney(inv.outstanding_amount, detail.header.currency) }}</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- Tracking timeline -->
					<div v-if="detail.tracking.length" class="sd-card">
						<div class="sd-card-title">Recent Tracking Updates</div>
						<ul class="sd-list">
							<li v-for="(t, idx) in detail.tracking" :key="idx" style="display: block;">
								<div style="display: flex; justify-content: space-between;">
									<strong style="font-size: 12px;">{{ t.source }}</strong>
									<span class="sd-muted" style="font-size: 12px;">{{ formatDateTime(t.date) }}</span>
								</div>
								<div style="font-size: 13px; margin-top: 2px;">{{ t.event }}</div>
							</li>
						</ul>
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "../api";
import { formatMoney, formatDate, formatDateTime } from "../format";
import StatusBadge from "./StatusBadge.vue";
import KpiCard from "./KpiCard.vue";

const props = defineProps({
	jobName: { type: String, required: true },
});
defineEmits(["close"]);

const loading = ref(true);
const error = ref("");
const detail = ref(null);

const shipmentStages = computed(() => {
	if (!detail.value) return [];
	const d = detail.value.shipment_dates;
	const isImport = detail.value.header.direction === "Import";
	return [
		{ label: "Booking Confirmed", date: d.booking_date, done: !!d.booking_date },
		{ label: "Cargo Ready", date: d.cargo_ready_date, done: !!d.cargo_ready_date },
		{ label: isImport ? "Departed Origin (ATD)" : "Estimated Departure", date: d.atd || d.etd, done: !!d.atd },
		{ label: isImport ? "Arrived (ATA)" : "Departed (ATD)", date: d.ata || d.atd, done: isImport ? !!d.ata : !!d.atd },
		{ label: "Discharged", date: d.discharge_date, done: !!d.discharge_date },
		{ label: "Completed", date: d.completed_on, done: !!d.completed_on },
	];
});

function tickCross(val) {
	return val ? "\u2713" : "\u2717";
}

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
