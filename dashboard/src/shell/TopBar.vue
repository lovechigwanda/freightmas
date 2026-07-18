<template>
	<header class="cc-topbar">
		<div class="cc-topbar-titles">
			<div class="cc-topbar-title">{{ currentTitle }}</div>
			<div class="cc-topbar-sub">{{ branding.company_name || "FreightMas" }} &middot; {{ today }}</div>
		</div>

		<div class="cc-topbar-actions">
			<button class="cc-topbar-iconbtn" title="Refresh data" @click="refresh">
				<RefreshCw :size="16" stroke-width="2" />
			</button>
			<a class="cc-topbar-iconbtn" :href="deskLink" title="Open in Frappe Desk">
				<ExternalLink :size="16" stroke-width="2" />
			</a>
			<a class="cc-topbar-iconbtn" href="/app" title="Back to Desk">
				<LayoutGrid :size="16" stroke-width="2" />
			</a>
		</div>
	</header>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { RefreshCw, ExternalLink, LayoutGrid } from "@lucide/vue";
import { NAV_ITEMS } from "../router";
import { useOverviewStore } from "../stores/overview";

const overview = useOverviewStore();

defineProps({
	branding: { type: Object, default: () => ({}) },
});

const route = useRoute();
const currentTitle = computed(() => {
	const match = NAV_ITEMS.find((item) => item.name === route.name);
	return match ? match.label : "FreightMas";
});

const today = new Date().toLocaleDateString(undefined, { weekday: "long", day: "2-digit", month: "short", year: "numeric" });

// Forwarding module is the only one backed by real Desk data so far -
// everything else falls back to the Desk home.
const deskLink = computed(() => {
	if (route.name === "overview" || route.name === "forwarding") return "/app/forwarding-job";
	return "/app";
});

function refresh() {
	// Prefer an in-place data refetch on the executive overview; other module
	// routes fall back to a full reload until they get their own stores.
	if (route.name === "overview") {
		overview.refresh();
	} else {
		window.location.reload();
	}
}
</script>
