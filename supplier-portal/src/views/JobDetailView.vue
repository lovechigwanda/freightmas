<template>
	<div>
		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 6" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="detail">
			<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
				<router-link to="/jobs" class="sd-table-link">&larr; Back to My Jobs</router-link>
				<span style="font-weight: 600; font-size: 15px;">{{ detail.header.name }}</span>
				<StatusBadge :status="detail.header.status" />
			</div>

			<div class="sd-card" style="margin-bottom: 14px;">
				<div class="sd-card-title"><span class="sd-card-title-main">Job Details</span></div>
				<ul class="sd-list">
					<li v-if="detail.header.direction"><span class="sd-muted">Direction</span><span>{{ detail.header.direction }}</span></li>
					<li v-if="'port_of_loading' in detail.header || 'origin' in detail.header">
						<span class="sd-muted">Route</span>
						<span>{{ detail.header.port_of_loading || detail.header.origin || "–" }} &rarr; {{ detail.header.port_of_discharge || detail.header.destination || "–" }}</span>
					</li>
					<li v-if="'bl_number' in detail.header"><span class="sd-muted">BL Number</span><span>{{ detail.header.bl_number || "–" }}</span></li>
					<li v-if="'vessel_flight_no' in detail.header"><span class="sd-muted">Vessel / Flight</span><span>{{ detail.header.vessel_flight_no || "–" }}</span></li>
					<li v-if="'eta' in detail.header"><span class="sd-muted">ETA / ATA</span><span>{{ formatDate(detail.header.eta) }} &middot; {{ detail.header.ata ? formatDate(detail.header.ata) : "Pending" }}</span></li>
					<li v-if="'etd' in detail.header"><span class="sd-muted">ETD / ATD</span><span>{{ formatDate(detail.header.etd) }} &middot; {{ detail.header.atd ? formatDate(detail.header.atd) : "Pending" }}</span></li>
					<li v-if="detail.header.cargo_description"><span class="sd-muted">Cargo</span><span>{{ detail.header.cargo_description }}<span v-if="detail.header.cargo_count"> &middot; {{ detail.header.cargo_count }}</span></span></li>
				</ul>
				<div v-if="detail.header.current_comment" class="sd-muted" style="margin-top: 12px; font-size: 13px;">
					Latest update: {{ detail.header.current_comment }}
				</div>
			</div>

			<div v-for="(rows, fieldname) in detail.charges" :key="fieldname" class="sd-card" style="margin-bottom: 14px;">
				<div class="sd-card-title"><span class="sd-card-title-main">{{ chargeGroupLabel(fieldname) }} ({{ rows.length }})</span></div>
				<table class="sd-table" v-if="rows.length">
					<thead>
						<tr>
							<th>Charge</th>
							<th v-if="hasColumn(rows, 'qty')">Qty</th>
							<th v-if="hasColumn(rows, 'buy_rate')">Rate</th>
							<th v-if="hasColumn(rows, 'cost_amount')">Amount</th>
							<th v-if="hasColumn(rows, 'is_purchased')">Invoiced</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="row in rows" :key="row.name">
							<td>{{ row.charge || row.transporter || "–" }}<div v-if="row.description" class="sd-muted" style="font-size: 12px;">{{ row.description }}</div></td>
							<td v-if="hasColumn(rows, 'qty')">{{ row.qty ?? "–" }}</td>
							<td v-if="hasColumn(rows, 'buy_rate')">{{ formatMoney(row.buy_rate) }}</td>
							<td v-if="hasColumn(rows, 'cost_amount')">{{ formatMoney(row.cost_amount) }}</td>
							<td v-if="hasColumn(rows, 'is_purchased')">{{ row.is_purchased ? "Yes" : "No" }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="Receipt" title="No charges on this job for you yet" />
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { Receipt } from "@lucide/vue";
import { api } from "../api/jobs";
import { formatDate, formatMoney } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";

const props = defineProps({
	jobDoctype: { type: String, required: true },
	jobName: { type: String, required: true },
});

const detail = ref(null);
const loading = ref(true);
const error = ref("");

const CHARGE_GROUP_LABELS = {
	forwarding_costing_charges: "Charges",
	forwarding_cost_charges: "Cost Lines",
	clearing_costing_charges: "Charges",
	clearing_cost_charges: "Cost Lines",
	border_clearing_costing_charges: "Charges",
	border_clearing_cost_charges: "Cost Lines",
	road_freight_charges: "Charges",
	truck_loading_details: "Truck Loads",
};

function chargeGroupLabel(fieldname) {
	return CHARGE_GROUP_LABELS[fieldname] || fieldname;
}

function hasColumn(rows, key) {
	return rows.some((r) => key in r);
}

async function load(jobDoctype, jobName) {
	loading.value = true;
	error.value = "";
	try {
		detail.value = await api.getJobDetail(jobDoctype, jobName);
	} catch (e) {
		error.value = e.message || "Failed to load this job.";
	} finally {
		loading.value = false;
	}
}

watch(
	() => [props.jobDoctype, props.jobName],
	([jobDoctype, jobName]) => jobDoctype && jobName && load(jobDoctype, jobName),
	{ immediate: true }
);
</script>
