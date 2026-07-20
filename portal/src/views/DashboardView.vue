<template>
	<div>
		<div v-if="loading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 3" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>

		<template v-else-if="data">
			<div class="cc-overview-meta">
				<span class="sd-muted">Welcome back, {{ fullName || "there" }}.</span>
			</div>

			<div class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
				<KpiCard label="Active Shipments" :value="formatNumber(data.active_shipments)" :icon="Boxes" />
				<KpiCard label="In Transit" :value="formatNumber(data.in_transit)" :icon="Ship" />
				<KpiCard
					label="Needs Attention"
					:value="formatNumber(data.overdue)"
					:tone="data.overdue ? 'warn' : 'good'"
					:icon="AlertTriangle"
					sub="Past ETA/ETD, unconfirmed"
				/>
				<KpiCard
					label="Outstanding"
					:value="formatMoney(data.outstanding_amount)"
					:tone="data.outstanding_amount ? 'warn' : 'good'"
					:icon="Wallet"
				/>
				<KpiCard
					label="Overdue Invoices"
					:value="formatMoney(data.overdue_amount)"
					:tone="data.overdue_amount ? 'danger' : 'good'"
					:icon="Receipt"
				/>
			</div>

			<div class="sd-card">
				<div class="sd-card-title">
					<span class="sd-card-title-main">Recent Shipments</span>
					<router-link to="/shipments" class="sd-table-link" style="font-size: 12px;">View all &rarr;</router-link>
				</div>
				<table class="sd-table" v-if="data.recent_jobs.length">
					<thead>
						<tr>
							<th>Job / Reference</th>
							<th>Route</th>
							<th>Status</th>
							<th>ETA</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="job in data.recent_jobs" :key="job.name">
							<td>
								<button class="sd-table-link" @click="openJob(job.name)">{{ job.name }}</button>
								<div class="sd-muted" style="font-size: 12px;">{{ job.customer_reference || "–" }}</div>
							</td>
							<td>{{ job.port_of_loading || "–" }} &rarr; {{ job.destination || job.port_of_discharge || "–" }}</td>
							<td><StatusBadge :status="job.status" /></td>
							<td>{{ formatDate(job.eta) }}</td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="Ship" title="No shipments yet" sub="Your active shipments will show up here." />
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { Boxes, Ship, AlertTriangle, Wallet, Receipt } from "@lucide/vue";
import { api } from "../api/dashboard";
import { formatDate, formatNumber, formatMoney } from "../format";
import { useSessionStore } from "../stores/session";
import KpiCard from "../components/KpiCard.vue";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";
import { useRouter } from "vue-router";

const router = useRouter();
const session = useSessionStore();
const { fullName } = storeToRefs(session);

const data = ref(null);
const loading = ref(true);
const error = ref("");

async function load() {
	loading.value = true;
	error.value = "";
	try {
		data.value = await api.getOverview();
	} catch (e) {
		error.value = e.message || "Failed to load your dashboard.";
	} finally {
		loading.value = false;
	}
}

function openJob(name) {
	router.push(`/shipments/${encodeURIComponent(name)}`);
}

onMounted(load);
</script>
