<template>
	<div>
		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 6" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="detail">
			<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
				<router-link to="/shipments" class="sd-table-link">&larr; Back to Shipments</router-link>
				<span style="font-weight: 600; font-size: 15px;">{{ detail.header.name }}</span>
				<StatusBadge :status="detail.header.status" />
			</div>

			<nav class="sd-tabs">
				<button class="sd-tab" :class="{ active: tab === 'overview' }" @click="tab = 'overview'">Overview</button>
				<button class="sd-tab" :class="{ active: tab === 'tracking' }" @click="tab = 'tracking'">Tracking &amp; Milestones</button>
			</nav>

			<div v-if="tab === 'overview'" class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main">Shipment Details</span></div>
					<ul class="sd-list">
						<li><span class="sd-muted">Route</span><span>{{ detail.header.port_of_loading || "–" }} &rarr; {{ detail.header.destination || detail.header.port_of_discharge || "–" }}</span></li>
						<li><span class="sd-muted">Mode / Type</span><span>{{ detail.header.shipment_mode || "–" }} &middot; {{ detail.header.shipment_type || "–" }}</span></li>
						<li><span class="sd-muted">Direction</span><span>{{ detail.header.direction || "–" }}</span></li>
						<li><span class="sd-muted">Vessel / Flight</span><span>{{ detail.header.vessel_flight_no || "–" }}</span></li>
						<li><span class="sd-muted">BL Number</span><span>{{ detail.header.bl_number || "–" }}</span></li>
						<li><span class="sd-muted">Incoterms</span><span>{{ detail.header.incoterms || "–" }}</span></li>
						<li><span class="sd-muted">Customer Reference</span><span>{{ detail.header.customer_reference || "–" }}</span></li>
						<li><span class="sd-muted">Cargo</span><span>{{ detail.header.cargo_description || "–" }}<span v-if="detail.header.cargo_count"> &middot; {{ detail.header.cargo_count }}</span></span></li>
					</ul>
				</div>

				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main">Dates</span></div>
					<ul class="sd-list">
						<li><span class="sd-muted">Booking Date</span><span>{{ formatDate(detail.shipment_dates.booking_date) }}</span></li>
						<li><span class="sd-muted">ETD / ATD</span><span>{{ formatDate(detail.shipment_dates.etd) }} &middot; {{ detail.shipment_dates.atd ? formatDate(detail.shipment_dates.atd) : "Pending" }}</span></li>
						<li><span class="sd-muted">ETA / ATA</span><span>{{ formatDate(detail.shipment_dates.eta) }} &middot; {{ detail.shipment_dates.ata ? formatDate(detail.shipment_dates.ata) : "Pending" }}</span></li>
						<li><span class="sd-muted">Discharge Date</span><span>{{ formatDate(detail.shipment_dates.discharge_date) }}</span></li>
						<li><span class="sd-muted">Completed On</span><span>{{ formatDate(detail.shipment_dates.completed_on) }}</span></li>
					</ul>
					<div v-if="detail.header.current_comment" class="sd-muted" style="margin-top: 12px; font-size: 13px;">
						Latest update: {{ detail.header.current_comment }}
					</div>
				</div>
			</div>

			<template v-else>
				<div v-for="group in detail.milestone_stages" :key="group.group" class="sd-card" style="margin-bottom: 14px;">
					<div class="sd-card-title"><span class="sd-card-title-main">{{ group.group }}</span></div>
					<div class="sd-stage-group">
						<div class="sd-stage-grid">
							<div v-for="m in group.milestones" :key="m.label" class="sd-stage-row">
								<span class="sd-stage-dot" :class="m.is_completed ? 'done' : 'pending'">
									<Check v-if="m.is_completed" :size="12" stroke-width="3" />
								</span>
								<span class="sd-stage-label">{{ m.label }}</span>
								<span class="sd-stage-date">{{ m.completed_on ? formatDate(m.completed_on) : "Pending" }}</span>
							</div>
						</div>
					</div>
				</div>

				<div v-if="detail.cargo.length" class="sd-card" style="margin-bottom: 14px;">
					<div class="sd-card-title"><span class="sd-card-title-main">Cargo / Containers ({{ detail.cargo.length }})</span></div>
					<table class="sd-table">
						<thead>
							<tr>
								<th>Container / Item</th>
								<th>Type</th>
								<th>Status</th>
								<th>Location</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in detail.cargo" :key="row.name">
								<td>{{ row.container_number || "–" }}</td>
								<td>{{ row.container_type || row.cargo_type || "–" }}</td>
								<td>{{ cargoStatus(row) }}</td>
								<td>{{ row.truck_location || "–" }}</td>
							</tr>
						</tbody>
					</table>
				</div>

				<div class="sd-card">
					<div class="sd-card-title"><span class="sd-card-title-main">Tracking Timeline</span></div>
					<ul class="sd-list" v-if="detail.tracking.length">
						<li v-for="(event, idx) in detail.tracking" :key="idx">
							<span class="cc-list-label">
								<span class="cc-list-text">{{ event.event }}</span>
							</span>
							<span class="sd-muted" style="font-size: 12px;">{{ formatDate(event.date) }}</span>
						</li>
					</ul>
					<EmptyState v-else :icon="Clock" title="No tracking events yet" />
				</div>
			</template>
		</template>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { Check, Clock } from "@lucide/vue";
import { api } from "../api/shipments";
import { formatDate } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";

const props = defineProps({ id: { type: String, required: true } });

const detail = ref(null);
const loading = ref(true);
const error = ref("");
const tab = ref("overview");

async function load(jobName) {
	loading.value = true;
	error.value = "";
	try {
		detail.value = await api.getJobDetail(jobName);
	} catch (e) {
		error.value = e.message || "Failed to load this shipment.";
	} finally {
		loading.value = false;
	}
}

function cargoStatus(row) {
	if (row.is_completed) return "Completed";
	if (row.is_returned) return "Returned";
	if (row.is_offloaded) return "Offloaded";
	if (row.is_loaded) return "Loaded";
	if (row.is_booked) return "Booked";
	return "Pending";
}

watch(() => props.id, (id) => id && load(id), { immediate: true });
</script>
