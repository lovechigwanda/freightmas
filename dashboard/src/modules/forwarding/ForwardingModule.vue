<template>
	<div>
		<nav class="sd-tabs">
			<button
				v-for="tab in tabs"
				:key="tab.key"
				class="sd-tab"
				:class="{ active: activeTab === tab.key }"
				@click="activeTab = tab.key"
			>
				<component :is="tab.icon" :size="14" stroke-width="2" style="margin-right: 6px; vertical-align: -2px;" />
				{{ tab.label }}
			</button>
		</nav>

		<main class="sd-body" style="padding: 0;">
			<OverviewView v-if="activeTab === 'overview'" @open-job="openJob" />
			<ShipmentsView v-else-if="activeTab === 'shipments'" @open-job="openJob" />
			<FinanceView v-else-if="activeTab === 'finance'" @open-job="openJob" />
			<DndView v-else-if="activeTab === 'dnd'" @open-job="openJob" />
		</main>

		<JobDetailModal v-if="selectedJob" :job-name="selectedJob" @close="selectedJob = null" />
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { LayoutDashboard, Ship, Wallet, AlertTriangle } from "@lucide/vue";
import OverviewView from "./OverviewView.vue";
import ShipmentsView from "./ShipmentsView.vue";
import FinanceView from "./FinanceView.vue";
import DndView from "./DndView.vue";
import JobDetailModal from "./JobDetailModal.vue";

const tabs = [
	{ key: "overview", label: "Overview", icon: LayoutDashboard },
	{ key: "shipments", label: "Shipments", icon: Ship },
	{ key: "finance", label: "Finance", icon: Wallet },
	{ key: "dnd", label: "DND & Additional Costs", icon: AlertTriangle },
];

const route = useRoute();
const router = useRouter();
const validKeys = tabs.map((t) => t.key);

// Deep-linkable tabs (?tab=shipments) so a specific view can be bookmarked
// or shared instead of always landing back on Overview.
const activeTab = ref(validKeys.includes(route.query.tab) ? route.query.tab : "overview");
const selectedJob = ref(null);

watch(activeTab, (key) => {
	router.replace({ query: { ...route.query, tab: key === "overview" ? undefined : key } });
});

function openJob(jobName) {
	selectedJob.value = jobName;
}
</script>
