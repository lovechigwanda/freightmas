<template>
	<div v-if="rows.length" class="sd-card">
		<div class="sd-card-title">
			<span class="sd-card-title-main">Containers ({{ rows.length }})</span>
		</div>
		<div class="sd-cargo-table-wrap">
			<table class="sd-table sd-cargo-table sd-cargo-table--client">
				<thead>
					<tr>
						<th>Container</th>
						<th>Type</th>
						<th>Status</th>
						<th>Last event</th>
						<th>Date</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					<template v-for="(row, idx) in rows" :key="idx">
						<tr class="sd-cargo-row" @click="toggleRow(idx)">
							<td class="sd-cargo-row-id">{{ row.container_number }}</td>
							<td>{{ row.container_type || "–" }}</td>
							<td>
								<span class="sd-cargo-status" :class="statusClass(row.status)">
									{{ row.status || "–" }}
								</span>
							</td>
							<td>{{ row.last_event || "–" }}</td>
							<td>{{ row.last_event_date ? formatDate(row.last_event_date) : "–" }}</td>
							<td class="sd-cargo-expand-cell">
								<ChevronDown
									:size="16"
									:class="{ 'sd-cargo-chevron--open': expanded.has(idx) }"
								/>
							</td>
						</tr>
						<tr v-if="expanded.has(idx)" class="sd-cargo-detail-row">
							<td colspan="6">
								<div class="sd-cargo-detail-grid">
									<div v-if="row.discharge_date">
										<span class="sd-muted">Discharged</span>
										<div>{{ formatDate(row.discharge_date) }}</div>
									</div>
									<div v-if="row.gate_out_date">
										<span class="sd-muted">Gate out</span>
										<div>{{ formatDate(row.gate_out_date) }}</div>
									</div>
									<div v-if="row.to_be_returned && row.empty_return_date">
										<span class="sd-muted">Empty return</span>
										<div>{{ formatDate(row.empty_return_date) }}</div>
									</div>
									<div v-if="row.is_truck_required && row.booked_on_date">
										<span class="sd-muted">Booked</span>
										<div>{{ formatDate(row.booked_on_date) }}</div>
									</div>
									<div v-if="row.is_truck_required && row.loaded_on_date">
										<span class="sd-muted">Loaded</span>
										<div>{{ formatDate(row.loaded_on_date) }}</div>
									</div>
									<div v-if="row.is_truck_required && row.offloaded_on_date">
										<span class="sd-muted">Offloaded</span>
										<div>{{ formatDate(row.offloaded_on_date) }}</div>
									</div>
									<div v-if="row.is_truck_required && row.completed_on_date">
										<span class="sd-muted">Completed</span>
										<div>{{ formatDate(row.completed_on_date) }}</div>
									</div>
								</div>
							</td>
						</tr>
					</template>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import { ChevronDown } from "@lucide/vue";
import { formatDate } from "../format";

const props = defineProps({
	containers: { type: Array, default: () => [] },
});

const expanded = ref(new Set());

const rows = computed(() => props.containers || []);

function toggleRow(idx) {
	const next = new Set(expanded.value);
	if (next.has(idx)) {
		next.delete(idx);
	} else {
		next.add(idx);
	}
	expanded.value = next;
}

function statusClass(status) {
	if (!status) return "";
	const normalized = status.toLowerCase();
	if (normalized.includes("deliver")) return "sd-cargo-status--delivered";
	if (normalized.includes("transit")) return "sd-cargo-status--transit";
	return "";
}
</script>
