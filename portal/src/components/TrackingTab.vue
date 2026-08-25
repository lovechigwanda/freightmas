<template>
	<div>
		<TrackingBanner v-if="view?.banner" :banner="view.banner" />

		<div
			v-for="section in view?.sections || []"
			:key="section.title"
			class="sd-card"
			style="margin-bottom: 14px;"
		>
			<div class="sd-card-title">
				<span class="sd-card-title-main">
					<span class="sd-card-title-icon"><ListChecks /></span>
					{{ section.title }}
				</span>
				<span
					v-if="section.progress"
					class="sd-progress-badge"
					:class="progressTone(section.progress.percent)"
				>
					{{ section.progress.done }}/{{ section.progress.total }} &middot; {{ section.progress.percent }}%
				</span>
			</div>

			<!-- Sea / Air -->
			<template v-if="section.kind === 'sea_air'">
				<div class="sd-stage-group">
					<div class="sd-stage-grid">
						<div
							v-for="stage in section.shipment_stages"
							:key="stage.label"
							class="sd-stage-row"
						>
							<span class="sd-stage-dot" :class="stage.done ? 'done' : 'pending'">
								<Check v-if="stage.done" :size="12" stroke-width="3" />
							</span>
							<span class="sd-stage-label">{{ stage.label }}</span>
							<span class="sd-stage-date">{{ stage.date ? formatDate(stage.date) : "Pending" }}</span>
						</div>
					</div>
				</div>
				<div v-if="section.containers?.length" class="sd-stage-group">
					<div class="sd-stage-group-title">Cargo / Containers ({{ section.containers.length }})</div>
					<table class="sd-table">
						<thead>
							<tr>
								<th>Container / Item</th>
								<th>Type</th>
								<th>Discharged</th>
								<th>Gate Out</th>
								<th>Empty Returned</th>
								<th>Status</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(row, idx) in section.containers" :key="idx">
								<td>{{ row.container_number }}</td>
								<td>{{ row.container_type || "–" }}</td>
								<td>
									<template v-if="row.discharge_date">{{ formatDate(row.discharge_date) }}</template>
									<TickCross v-else :value="false" />
								</td>
								<td>
									<template v-if="row.gate_out_date">{{ formatDate(row.gate_out_date) }}</template>
									<TickCross v-else :value="false" />
								</td>
								<td>
									<template v-if="row.to_be_returned">
										<template v-if="row.empty_return_date">{{ formatDate(row.empty_return_date) }}</template>
										<TickCross v-else :value="false" />
									</template>
									<span v-else class="sd-muted">–</span>
								</td>
								<td>{{ row.status || "–" }}</td>
							</tr>
						</tbody>
					</table>
				</div>
			</template>

			<!-- Road -->
			<template v-else-if="section.kind === 'road'">
				<table class="sd-table">
					<thead>
						<tr>
							<th>Container / Item</th>
							<th>Type</th>
							<th>Booked</th>
							<th>Loaded</th>
							<th>Offloaded</th>
							<th>Returned</th>
							<th>Completed</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(row, idx) in section.containers" :key="idx">
							<td>{{ row.container_number }}</td>
							<td>{{ row.container_type || "–" }}</td>
							<td>
								<template v-if="row.booked_on_date">{{ formatDate(row.booked_on_date) }}</template>
								<TickCross v-else :value="!!row.is_booked" />
							</td>
							<td>
								<template v-if="row.loaded_on_date">{{ formatDate(row.loaded_on_date) }}</template>
								<TickCross v-else :value="!!row.is_loaded" />
							</td>
							<td>
								<template v-if="row.offloaded_on_date">{{ formatDate(row.offloaded_on_date) }}</template>
								<TickCross v-else :value="!!row.is_offloaded" />
							</td>
							<td>
								<template v-if="row.cargo_type === 'Containerised' && row.to_be_returned">
									<template v-if="row.returned_on_date || row.empty_return_date">
										{{ formatDate(row.returned_on_date || row.empty_return_date) }}
									</template>
									<TickCross v-else :value="!!(row.is_returned || row.empty_return_date)" />
								</template>
								<span v-else class="sd-muted">–</span>
							</td>
							<td>
								<template v-if="row.completed_on_date">{{ formatDate(row.completed_on_date) }}</template>
								<TickCross v-else :value="!!row.is_completed" />
							</td>
						</tr>
					</tbody>
				</table>
			</template>

			<!-- Clearance stages (Stage Summary) -->
			<template v-else-if="section.kind === 'clearance_stages'">
				<ul class="sd-list sd-stage-list">
					<li
						v-for="st in section.stages"
						:key="st.name"
						:class="{ 'sd-stage-current': st.is_current }"
					>
						<span>
							{{ st.name }}
							<span v-if="st.is_current" class="sd-stage-badge">Current</span>
						</span>
						<span class="sd-muted">{{ st.done }}/{{ st.total }} &middot; {{ st.pct }}%</span>
					</li>
				</ul>
			</template>

			<!-- Clearance checklist (Full Milestones) -->
			<template v-else-if="section.kind === 'clearance_checklist'">
				<div class="sd-stage-group">
					<div class="sd-stage-grid">
						<div v-for="entry in section.entries" :key="entry.label" class="sd-stage-row">
							<span class="sd-stage-dot" :class="entry.is_completed ? 'done' : 'pending'">
								<Check v-if="entry.is_completed" :size="12" stroke-width="3" />
							</span>
							<span class="sd-stage-label">{{ entry.label }}</span>
							<span class="sd-stage-date">
								{{ entry.completed_on ? formatDate(entry.completed_on) : "Pending" }}
							</span>
						</div>
					</div>
				</div>
			</template>

			<!-- Completion -->
			<template v-else-if="section.kind === 'completion'">
				<div class="sd-stage-group">
					<div class="sd-stage-grid">
						<div class="sd-stage-row sd-stage-row-completion">
							<span class="sd-stage-dot" :class="section.completed ? 'done' : 'pending'">
								<Check v-if="section.completed" :size="12" stroke-width="3" />
							</span>
							<span class="sd-stage-label">Completed</span>
							<span class="sd-stage-date">
								{{ section.completed_on ? formatDate(section.completed_on) : "Pending" }}
							</span>
						</div>
					</div>
				</div>
			</template>
		</div>

		<div class="sd-card">
			<div class="sd-card-title">
				<span class="sd-card-title-main">
					<span class="sd-card-title-icon"><History /></span>
					Recent Updates
				</span>
			</div>
			<ul v-if="view?.live_updates?.length" class="sd-list">
				<li v-for="(item, idx) in view.live_updates" :key="idx" style="display: block;">
					<div style="display: flex; justify-content: space-between;">
						<strong style="font-size: 12px;">{{ item.source || "Update" }}</strong>
						<span class="sd-muted" style="font-size: 12px;">{{ formatDateTime(item.date) }}</span>
					</div>
					<div style="font-size: 13px; margin-top: 2px;">{{ item.event }}</div>
				</li>
			</ul>
			<EmptyState v-else :icon="Clock" title="No tracking updates yet" />
		</div>
	</div>
</template>

<script setup>
import { Check, Clock, History, ListChecks } from "@lucide/vue";
import { formatDate, formatDateTime } from "../format";
import EmptyState from "./EmptyState.vue";
import TickCross from "./TickCross.vue";
import TrackingBanner from "./TrackingBanner.vue";

defineProps({
	view: { type: Object, default: null },
});

function progressTone(percent) {
	if (percent >= 100) return "done";
	if (percent > 0) return "partial";
	return "pending";
}
</script>
