<template>
	<div>
		<div v-if="loading" class="sd-state">Loading overview...</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Active Shipments" :value="data.kpis.active_jobs" />
				<KpiCard
					label="Overdue Arrivals"
					:value="data.kpis.overdue_arrivals"
					:tone="data.kpis.overdue_arrivals ? 'danger' : ''"
					sub="Import ETA passed, no ATA"
				/>
				<KpiCard
					label="Overdue Departures"
					:value="data.kpis.overdue_departures"
					:tone="data.kpis.overdue_departures ? 'danger' : ''"
					sub="Export ETD passed, no ATD"
				/>
				<KpiCard
					label="Missing BL Docs"
					:value="data.kpis.missing_bl_docs"
					:tone="data.kpis.missing_bl_docs ? 'warn' : ''"
				/>
				<KpiCard
					label="Uninvoiced Jobs"
					:value="data.kpis.uninvoiced_jobs"
					:tone="data.kpis.uninvoiced_jobs ? 'warn' : ''"
				/>
				<KpiCard
					label="Open DND Exposure"
					:value="formatMoney(data.kpis.dnd_exposure)"
					:sub="`${data.kpis.dnd_jobs} job(s)`"
					:tone="data.kpis.dnd_exposure ? 'warn' : ''"
				/>
				<KpiCard
					label="Overdue Container Returns"
					:value="data.kpis.overdue_container_returns"
					:tone="data.kpis.overdue_container_returns ? 'danger' : ''"
				/>
			</div>

			<div class="sd-grid sd-grid-2">
				<div class="sd-card">
					<div class="sd-card-title">Jobs by Status</div>
					<div v-for="row in data.jobs_by_status" :key="row.status" style="margin-bottom: 8px;">
						<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
							<span>{{ row.status }}</span>
							<span class="sd-muted">{{ row.count }}</span>
						</div>
						<div style="height: 8px; background: #eef0f3; border-radius: 4px; overflow: hidden;">
							<div
								:style="{
									width: maxStatus ? (row.count / maxStatus) * 100 + '%' : '0%',
									height: '100%',
									background: 'var(--sd-primary-light)',
								}"
							></div>
						</div>
					</div>
				</div>

				<div class="sd-card">
					<div class="sd-card-title">Monthly Revenue &amp; Margin (last 6 months)</div>
					<table class="sd-table">
						<thead>
							<tr><th>Month</th><th class="sd-right">Shipments</th><th class="sd-right">Revenue</th><th class="sd-right">Margin</th></tr>
						</thead>
						<tbody>
							<tr v-for="row in data.monthly_trend" :key="row.period">
								<td>{{ row.period }}</td>
								<td class="sd-right">{{ row.shipment_count }}</td>
								<td class="sd-right">{{ formatMoney(row.revenue) }}</td>
								<td class="sd-right">{{ formatMoney(row.margin) }}</td>
							</tr>
						</tbody>
					</table>
				</div>

				<div class="sd-card">
					<div class="sd-card-title">Top Customers (Active Jobs)</div>
					<ul class="sd-list">
						<li v-for="row in data.top_customers" :key="row.customer">
							<span>{{ row.customer }}</span>
							<span class="sd-badge sd-badge-blue">{{ row.job_count }}</span>
						</li>
						<li v-if="!data.top_customers.length" class="sd-muted">No active jobs.</li>
					</ul>
				</div>

				<div class="sd-card">
					<div class="sd-card-title">Top Corridors</div>
					<ul class="sd-list">
						<li v-for="(row, idx) in data.top_corridors" :key="idx">
							<span>{{ row.port_of_loading }} &rarr; {{ row.port_of_discharge }}</span>
							<span class="sd-badge sd-badge-blue">{{ row.job_count }}</span>
						</li>
						<li v-if="!data.top_corridors.length" class="sd-muted">No data yet.</li>
					</ul>
				</div>
			</div>

			<div class="sd-card" style="margin-top: 16px;">
				<div class="sd-card-title">Recent Blockers / Exceptions</div>
				<table class="sd-table" v-if="data.recent_blockers.length">
					<thead>
						<tr><th>Job</th><th>Customer</th><th>Status</th><th>Comment</th><th>Updated</th></tr>
					</thead>
					<tbody>
						<tr v-for="row in data.recent_blockers" :key="row.name">
							<td><button class="sd-table-link" @click="$emit('open-job', row.name)">{{ row.name }}</button></td>
							<td>{{ row.customer }}</td>
							<td><StatusBadge :status="row.status" /></td>
							<td>{{ row.current_comment }}</td>
							<td class="sd-muted">{{ formatDate(row.last_updated_on) }}</td>
						</tr>
					</tbody>
				</table>
				<div v-else class="sd-muted" style="font-size: 13px;">No open blockers logged.</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "../api";
import { formatMoney, formatDate } from "../format";
import KpiCard from "../components/KpiCard.vue";
import StatusBadge from "../components/StatusBadge.vue";

defineEmits(["open-job"]);

const loading = ref(true);
const error = ref("");
const data = ref(null);

const maxStatus = computed(() => {
	if (!data.value) return 0;
	return Math.max(...data.value.jobs_by_status.map((r) => r.count), 1);
});

onMounted(async () => {
	try {
		data.value = await api.getOverview();
	} catch (e) {
		error.value = e.message || "Failed to load overview.";
	} finally {
		loading.value = false;
	}
});
</script>
