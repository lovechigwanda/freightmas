<template>
	<div>
		<div v-if="summary && !summaryLoading" class="sd-card" style="margin-bottom: 14px; padding: 16px 18px;">
			<div style="display: flex; flex-wrap: wrap; gap: 24px;">
				<div>
					<div class="sd-muted" style="font-size: 12px;">Awaiting approval</div>
					<div style="font-size: 20px; font-weight: 600;">{{ summary.pending_count }}</div>
				</div>
				<div>
					<div class="sd-muted" style="font-size: 12px;">Pending value</div>
					<div style="font-size: 20px; font-weight: 600;">{{ formatMoney(summary.pending_total) }}</div>
				</div>
				<div v-if="summary.expiring_soon_count">
					<div class="sd-muted" style="font-size: 12px;">Expiring within 7 days</div>
					<div style="font-size: 20px; font-weight: 600; color: var(--sd-amber);">
						{{ summary.expiring_soon_count }}
					</div>
				</div>
			</div>
		</div>
		<div v-else-if="summaryLoading" class="sd-card cc-skeleton" style="height: 72px; margin-bottom: 14px;"></div>

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
					placeholder="Search quotation, reference..."
					@input="onFilterChange"
				/>
				<button
					v-if="search.trim()"
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
				<div v-if="quotations.length" class="sd-invoice-list">
					<QuotationListCard v-for="quote in quotations" :key="quote.name" :quotation="quote" />
				</div>
				<EmptyState
					v-else
					:icon="FileText"
					title="No quotations match these filters"
					sub="Try clearing the search or switching tabs."
				/>

				<div v-if="quotations.length" class="sd-invoice-list-footer">
					<span class="sd-muted" style="font-size: 12px;">{{ totalCount }} quotation(s)</span>
					<div style="display: flex; gap: 8px; align-items: center;">
						<button class="sd-table-link" :disabled="page === 0" @click="changePage(-1)">&larr; Prev</button>
						<button
							class="sd-table-link"
							:disabled="(page + 1) * pageSize >= totalCount"
							@click="changePage(1)"
						>
							Next &rarr;
						</button>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { FileText } from "@lucide/vue";
import { api } from "../api/quotations";
import { formatMoney } from "../format";
import EmptyState from "../components/EmptyState.vue";
import QuotationListCard from "../components/QuotationListCard.vue";

const statusTabs = [
	{ value: "pending", label: "Awaiting approval" },
	{ value: "approved", label: "Approved" },
	{ value: "job_created", label: "Job created" },
	{ value: "declined", label: "Declined" },
];

const status = ref("pending");
const search = ref("");
const quotations = ref([]);
const totalCount = ref(0);
const loading = ref(true);
const error = ref("");
const page = ref(0);
const pageSize = 20;

const summary = ref(null);
const summaryLoading = ref(true);

async function loadSummary() {
	summaryLoading.value = true;
	try {
		summary.value = await api.getQuotationsSummary();
	} catch (e) {
		summary.value = null;
	} finally {
		summaryLoading.value = false;
	}
}

async function loadList() {
	loading.value = true;
	error.value = "";
	try {
		const result = await api.getQuotations({
			status: status.value,
			search: search.value.trim() || undefined,
			limit_start: page.value * pageSize,
			limit_page_length: pageSize,
		});
		quotations.value = result.quotations || [];
		totalCount.value = result.total_count || 0;
	} catch (e) {
		error.value = e.message || "Failed to load quotations.";
	} finally {
		loading.value = false;
	}
}

function setStatus(value) {
	status.value = value;
	page.value = 0;
	loadList();
}

function onFilterChange() {
	page.value = 0;
	loadList();
}

function clearFilters() {
	search.value = "";
	page.value = 0;
	loadList();
}

function changePage(delta) {
	page.value = Math.max(0, page.value + delta);
	loadList();
}

onMounted(() => {
	loadSummary();
	loadList();
});
</script>
