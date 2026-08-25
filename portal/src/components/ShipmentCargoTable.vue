<template>
	<div v-if="rows.length" class="sd-card">
		<div class="sd-card-title">
			<span class="sd-card-title-main">Cargo / Containers ({{ rows.length }})</span>
		</div>
		<div class="sd-cargo-table-wrap">
			<table class="sd-table sd-cargo-table">
				<thead>
					<tr>
						<th rowspan="2">Container / Item</th>
						<th rowspan="2">Type</th>
						<th colspan="3" class="sd-cargo-group-head">Sea / Air</th>
						<th colspan="5" class="sd-cargo-group-head">Road</th>
						<th rowspan="2">Status</th>
					</tr>
					<tr>
						<th>Disch.</th>
						<th>Gate Out</th>
						<th>Empty Ret.</th>
						<th>Booked</th>
						<th>Loaded</th>
						<th>Offloaded</th>
						<th>Returned</th>
						<th>Completed</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, idx) in rows" :key="idx">
						<td>{{ row.container_number }}</td>
						<td>{{ row.container_type || "–" }}</td>
						<td>
							<template v-if="row.discharge_date">{{ formatDate(row.discharge_date) }}</template>
							<TickCross v-else-if="hasSeaAir(row)" :value="false" />
							<span v-else class="sd-muted">–</span>
						</td>
						<td>
							<template v-if="row.gate_out_date">{{ formatDate(row.gate_out_date) }}</template>
							<TickCross v-else-if="hasSeaAir(row)" :value="false" />
							<span v-else class="sd-muted">–</span>
						</td>
						<td>
							<template v-if="row.to_be_returned">
								<template v-if="row.empty_return_date">{{ formatDate(row.empty_return_date) }}</template>
								<TickCross v-else-if="hasSeaAir(row)" :value="false" />
							</template>
							<span v-else class="sd-muted">–</span>
						</td>
						<td>
							<template v-if="row.booked_on_date">{{ formatDate(row.booked_on_date) }}</template>
							<TickCross v-else-if="hasRoad(row)" :value="!!row.is_booked" />
							<span v-else class="sd-muted">–</span>
						</td>
						<td>
							<template v-if="row.loaded_on_date">{{ formatDate(row.loaded_on_date) }}</template>
							<TickCross v-else-if="hasRoad(row)" :value="!!row.is_loaded" />
							<span v-else class="sd-muted">–</span>
						</td>
						<td>
							<template v-if="row.offloaded_on_date">{{ formatDate(row.offloaded_on_date) }}</template>
							<TickCross v-else-if="hasRoad(row)" :value="!!row.is_offloaded" />
							<span v-else class="sd-muted">–</span>
						</td>
						<td>
							<template v-if="row.cargo_type === 'Containerised' && row.to_be_returned">
								<template v-if="row.returned_on_date || row.empty_return_date">
									{{ formatDate(row.returned_on_date || row.empty_return_date) }}
								</template>
								<TickCross v-else-if="hasRoad(row)" :value="!!(row.is_returned || row.empty_return_date)" />
							</template>
							<span v-else class="sd-muted">–</span>
						</td>
						<td>
							<template v-if="row.completed_on_date">{{ formatDate(row.completed_on_date) }}</template>
							<TickCross v-else-if="hasRoad(row)" :value="!!row.is_completed" />
							<span v-else class="sd-muted">–</span>
						</td>
						<td>{{ row.status || "–" }}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { formatDate } from "../format";
import { mergeCargoRows, roadSection, seaAirSection } from "../utils/shipmentView";
import TickCross from "./TickCross.vue";

const props = defineProps({
	view: { type: Object, default: null },
});

const rows = computed(() =>
	mergeCargoRows(seaAirSection(props.view?.sections), roadSection(props.view?.sections)),
);

function hasSeaAir(row) {
	return !!row.has_sea_air;
}

function hasRoad(row) {
	return !!row.has_road;
}
</script>
