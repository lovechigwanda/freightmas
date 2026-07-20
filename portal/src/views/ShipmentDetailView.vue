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
				<button class="sd-tab" :class="{ active: tab === 'tracking' }" @click="tab = 'tracking'">Tracking</button>
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
				<div class="sd-card" style="margin-bottom: 14px;">
					<div class="sd-card-title"><span class="sd-card-title-main">Journey</span></div>
					<Timeline v-if="timeline.length" :items="timeline" />
					<EmptyState v-else :icon="Clock" title="No tracking updates yet" />
				</div>

				<div v-if="detail.cargo.length" class="sd-card">
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
			</template>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { Clock } from "@lucide/vue";
import { api } from "../api/shipments";
import { formatDate } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";
import Timeline from "../components/Timeline.vue";

const props = defineProps({ id: { type: String, required: true } });

const detail = ref(null);
const loading = ref(true);
const error = ref("");
const tab = ref("overview");

// Merges the structured milestone checklist and the free-text tracking log
// into one chronological journey: completed milestones + logged events,
// newest first, followed by not-yet-completed milestones (no date yet).
const timeline = computed(() => {
	if (!detail.value) return [];

	const dated = [];
	const pending = [];
	for (const group of detail.value.milestone_stages || []) {
		for (const m of group.milestones) {
			if (m.is_completed && m.completed_on) {
				dated.push({ label: m.label, sub: group.group, date: m.completed_on, done: true });
			} else if (!m.is_completed) {
				pending.push({ label: m.label, sub: group.group, date: null, done: false });
			}
		}
	}
	for (const t of detail.value.tracking || []) {
		dated.push({ label: t.event, sub: t.source ? `via ${t.source}` : "", date: t.date, done: true });
	}
	dated.sort((a, b) => new Date(b.date) - new Date(a.date));

	if (pending.length) pending[0].next = true;

	return [...dated, ...pending];
});

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
