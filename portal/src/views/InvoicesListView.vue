<template>
	<div>
		<InvoiceAccountHeader
			v-if="summary && !summaryLoading"
			:summary="summary"
			:statement-url-builder="statementUrlBuilder"
			style="margin-bottom: 14px;"
		/>
		<div v-else-if="summaryLoading" class="sd-card cc-skeleton" style="height: 92px; margin-bottom: 14px;"></div>

		<InvoiceAgingStrip
			v-if="summary?.aging && !summaryLoading"
			:aging="summary.aging"
			:active-bucket="agingBucket"
			style="margin-bottom: 14px;"
			@select="setAgingBucket"
		/>

		<div class="sd-toolbar">
			<nav class="sd-tabs" style="margin-bottom: 0;">
				<button
					v-for="tab in statusTabs"
					:key="tab.value"
					class="sd-tab"
					:class="{ active: status === tab.value }"
					@click="setStatus(tab.value)"
				>
					{{ tab.label }}
				</button>
			</nav>

			<div class="sd-filters sd-invoices-toolbar-actions" style="margin-bottom: 0;">
				<input
					v-model="search"
					type="text"
					placeholder="Search invoice, job, reference..."
					@input="onFilterChange"
				/>
				<input v-model="fromDate" type="date" @change="onFilterChange" />
				<input v-model="toDate" type="date" @change="onFilterChange" />
				<button
					v-if="hasActiveFilters"
					type="button"
					class="sd-table-link"
					@click="clearFilters"
				>
					Clear filters
				</button>
			</div>
		</div>

		<div class="sd-card sd-invoice-list-panel">
			<div v-if="loading">
				<div class="cc-row-skeleton cc-skeleton" v-for="i in 8" :key="i"></div>
			</div>
			<div v-else-if="error" class="sd-state" style="color: var(--sd-red)">{{ error }}</div>
			<template v-else>
				<div v-if="invoices.length" class="sd-invoice-list">
					<InvoiceListCard v-for="inv in invoices" :key="inv.name" :invoice="inv" />
				</div>
				<EmptyState
					v-else
					:icon="Receipt"
					title="No invoices match these filters"
					sub="Try clearing the search, aging bucket, or date filters."
				/>

				<div v-if="invoices.length" class="sd-invoice-list-footer">
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
import { computed, onMounted, ref } from "vue";
import { Receipt } from "@lucide/vue";
import { api } from "../api/invoices";
import EmptyState from "../components/EmptyState.vue";
import InvoiceAccountHeader from "../components/InvoiceAccountHeader.vue";
import InvoiceAgingStrip from "../components/InvoiceAgingStrip.vue";
import InvoiceListCard from "../components/InvoiceListCard.vue";

const statusTabs = [
	{ value: "Outstanding", label: "Outstanding" },
	{ value: "Overdue", label: "Overdue" },
	{ value: "Paid", label: "Paid" },
	{ value: "", label: "All" },
];

const status = ref("Outstanding");
const agingBucket = ref("");
const search = ref("");
const fromDate = ref("");
const toDate = ref("");
const invoices = ref([]);
const totalCount = ref(0);
const loading = ref(true);
const error = ref("");
const page = ref(0);
const pageSize = 20;

const summary = ref(null);
const summaryLoading = ref(true);

const hasActiveFilters = computed(
	() => Boolean(search.value.trim() || fromDate.value || toDate.value || agingBucket.value),
);

function statementUrlBuilder(params = {}) {
	return api.exportStatementUrl({
		party: summary.value?.statement_party || undefined,
		from_date: fromDate.value || undefined,
		to_date: toDate.value || undefined,
		...params,
	});
}

let filterTimer;

function onFilterChange() {
	clearTimeout(filterTimer);
	filterTimer = setTimeout(() => {
		page.value = 0;
		load();
	}, 250);
}

function clearFilters() {
	search.value = "";
	fromDate.value = "";
	toDate.value = "";
	agingBucket.value = "";
	page.value = 0;
	load();
}

async function load() {
	loading.value = true;
	error.value = "";
	try {
		const res = await api.getInvoices({
			status: status.value,
			search: search.value.trim() || undefined,
			from_date: fromDate.value || undefined,
			to_date: toDate.value || undefined,
			aging_bucket: agingBucket.value || undefined,
			sort_by: status.value === "Outstanding" || status.value === "Overdue" ? "due_date" : "posting_date",
			sort_order: status.value === "Outstanding" || status.value === "Overdue" ? "asc" : "desc",
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
	} catch {
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

function setAgingBucket(bucket) {
	agingBucket.value = agingBucket.value === bucket ? "" : bucket;
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
