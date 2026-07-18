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
			<JobsView v-else-if="activeTab === 'jobs'" @open-job="openJob" />
			<FinanceView v-else-if="activeTab === 'finance'" @open-job="openJob" />
		</main>

		<ClearingJobDetailModal v-if="selectedJob" :job-name="selectedJob" @close="selectedJob = null" />
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { LayoutDashboard, ClipboardCheck, Wallet } from "@lucide/vue";
import OverviewView from "./OverviewView.vue";
import JobsView from "./JobsView.vue";
import FinanceView from "./FinanceView.vue";
import ClearingJobDetailModal from "./ClearingJobDetailModal.vue";

const tabs = [
	{ key: "overview", label: "Overview", icon: LayoutDashboard },
	{ key: "jobs", label: "Clearing Jobs", icon: ClipboardCheck },
	{ key: "finance", label: "Finance", icon: Wallet },
];

const route = useRoute();
const router = useRouter();
const validKeys = tabs.map((t) => t.key);
const activeTab = ref(validKeys.includes(route.query.tab) ? route.query.tab : "overview");
const selectedJob = ref(null);

watch(activeTab, (key) => {
	router.replace({ query: { ...route.query, tab: key === "overview" ? undefined : key } });
});

function openJob(jobName) {
	selectedJob.value = jobName;
}
</script>
