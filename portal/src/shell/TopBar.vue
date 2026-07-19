<template>
	<header class="cc-topbar">
		<div class="cc-topbar-titles">
			<span class="cc-topbar-title">{{ currentTitle }}</span>
			<span class="cc-topbar-sub">{{ customerLabel }} &middot; {{ today }}</span>
		</div>
	</header>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import { NAV_ITEMS } from "../router";
import { useSessionStore } from "../stores/session";

const route = useRoute();
const session = useSessionStore();
const { customers } = storeToRefs(session);

const currentTitle = computed(() => {
	const match = NAV_ITEMS.find((item) => item.name === route.name);
	return match ? match.label : "Client Portal";
});

const customerLabel = computed(() => {
	if (!customers.value.length) return "FreightMas";
	return customers.value.map((c) => c.customer_name || c.name).join(", ");
});

const today = new Date().toLocaleDateString(undefined, { weekday: "long", day: "2-digit", month: "short", year: "numeric" });
</script>
