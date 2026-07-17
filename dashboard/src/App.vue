<template>
	<div class="sd-app">
		<header class="sd-header">
			<div class="sd-brand">
				<img v-if="branding.logo" :src="branding.logo" :alt="branding.company_name" />
				<div v-else class="sd-brand-fallback">{{ brandInitials }}</div>
				<div>
					<div class="sd-brand-name">{{ branding.company_name || "FreightMas" }}</div>
					<div class="sd-brand-sub">{{ branding.address || "Freight &amp; Logistics Management" }}</div>
				</div>
			</div>
			<div class="sd-title">Shipment Dashboard</div>
		</header>

		<nav class="sd-tabs">
			<button
				v-for="tab in tabs"
				:key="tab.key"
				class="sd-tab"
				:class="{ active: activeTab === tab.key }"
				@click="activeTab = tab.key"
			>
				{{ tab.label }}
			</button>
		</nav>

		<main class="sd-body">
			<OverviewView v-if="activeTab === 'overview'" @open-job="openJob" />
			<ShipmentsView v-else-if="activeTab === 'shipments'" @open-job="openJob" />
			<FinanceView v-else-if="activeTab === 'finance'" @open-job="openJob" />
			<DndView v-else-if="activeTab === 'dnd'" @open-job="openJob" />
		</main>

		<JobDetailModal v-if="selectedJob" :job-name="selectedJob" @close="selectedJob = null" />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "./api";
import { initials } from "./format";
import OverviewView from "./views/OverviewView.vue";
import ShipmentsView from "./views/ShipmentsView.vue";
import FinanceView from "./views/FinanceView.vue";
import DndView from "./views/DndView.vue";
import JobDetailModal from "./components/JobDetailModal.vue";

const tabs = [
	{ key: "overview", label: "Overview" },
	{ key: "shipments", label: "Shipments" },
	{ key: "finance", label: "Finance" },
	{ key: "dnd", label: "DND & Additional Costs" },
];

const activeTab = ref("overview");
const branding = ref({});
const selectedJob = ref(null);

const brandInitials = computed(() => initials(branding.value.company_name));

function openJob(jobName) {
	selectedJob.value = jobName;
}

onMounted(async () => {
	try {
		branding.value = await api.getBranding();
	} catch (e) {
		branding.value = { company_name: "FreightMas" };
	}
});
</script>
