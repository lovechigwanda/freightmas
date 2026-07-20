<template>
	<div>
		<div v-if="summaryLoading" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<div class="sd-card cc-kpi-skeleton cc-skeleton" v-for="i in 3" :key="i"></div>
		</div>
		<div v-else-if="summary" class="sd-grid sd-grid-kpi" style="margin-bottom: 18px;">
			<KpiCard
				label="Outstanding"
				:value="formatMoney(summary.outstanding_amount)"
				:tone="summary.outstanding_amount ? 'warn' : 'good'"
				:icon="Wallet"
			/>
			<KpiCard
				label="Overdue"
				:value="formatMoney(summary.overdue_amount)"
				:tone="summary.overdue_amount ? 'danger' : 'good'"
				:icon="AlertTriangle"
			/>
			<KpiCard label="Paid (YTD)" :value="formatMoney(summary.paid_ytd)" tone="good" :icon="CheckCircle2" />
		</div>

		<div class="sd-toolbar">
			<nav class="sd-tabs" style="margin-bottom: 0;">
				<button
					v-for="t in statusTabs"
					:key="t.value"
					class="sd-tab"
					:class="{ active: status === t.value }"
					@click="setStatus(t.value)"
				>
					{{ t.label }}
				</button>
			</nav>
		</div>

		<div class="sd-card">
			<div v-if="loading">
				<div class="cc-row-skeleton cc-skeleton" v-for="i in 8" :key="i"></div>
			</div>
			<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>
			<template v-else>
				<table class="sd-table" v-if="invoices.length">
					<thead>
						<tr>
							<th>Invoice</th>
							<th>Shipment</th>
							<th>Due Date</th>
							<th>Amount</th>
							<th>Status</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="inv in invoices" :key="inv.name">
							<td><router-link class="sd-table-link" :to="`/invoices/${encodeURIComponent(inv.name)}`">{{ inv.name }}</router-link></td>
							<td>{{ inv.job_name || "–" }}</td>
							<td>{{ formatDate(inv.due_date) }}</td>
							<td>{{ formatMoney(inv.grand_total) }}</td>
							<td><StatusBadge :status="inv.status" /></td>
						</tr>
					</tbody>
				</table>
				<EmptyState v-else :icon="Receipt" title="No invoices match these filters" />

				<div v-if="invoices.length" style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px;">
					<span class="sd-muted" style="font-size: 12px;">{{ totalCount }} invoice(s)</span>
					<div style="display: flex; gap: 8px; align-items: center;">
						<button class="sd-table-link" :disabled="page === 0" @click="changePage(-1)">&larr; Prev</button>
						<button class="sd-table-link" :disabled="(page + 1) * pageSize >= totalCount" @click="changePage(1)">Next &rarr;</button>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { Receipt, Wallet, AlertTriangle, CheckCircle2 } from "@lucide/vue";
import { api } from "../api/invoices";
import { formatDate, formatMoney } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import EmptyState from "../components/EmptyState.vue";
import KpiCard from "../components/KpiCard.vue";

const statusTabs = [
	{ value: "", label: "All" },
	{ value: "Unpaid", label: "Unpaid" },
	{ value: "Overdue", label: "Overdue" },
	{ value: "Paid", label: "Paid" },
];

const status = ref("");
const invoices = ref([]);
const totalCount = ref(0);
const loading = ref(true);
const error = ref("");
const page = ref(0);
const pageSize = 20;

const summary = ref(null);
const summaryLoading = ref(true);

async function load() {
	loading.value = true;
	error.value = "";
	try {
		const res = await api.getInvoices({
			status: status.value,
			limit_start: page.value * pageSize,
			limit_page_length: pageSize,
		});
		invoices.value = res.invoices;
		totalCount.value = res.total_count;
	} catch (e) {
		error.value = e.message || "Failed to load invoices.";
	} finally {
		loading.value = false;
	}
}

async function loadSummary() {
	summaryLoading.value = true;
	try {
		summary.value = await api.getInvoicesSummary();
	} catch (e) {
		summary.value = null;
	} finally {
		summaryLoading.value = false;
	}
}

function setStatus(value) {
	if (status.value === value) return;
	status.value = value;
	page.value = 0;
	load();
}

function changePage(delta) {
	page.value += delta;
	load();
}

onMounted(() => {
	load();
	loadSummary();
});
</script>
