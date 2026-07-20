<template>
	<header class="cc-topbar">
		<div class="cc-topbar-titles">
			<span class="cc-topbar-title">{{ currentTitle }}</span>
			<span class="cc-topbar-sub">{{ supplierLabel }} &middot; {{ today }}</span>
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
const { suppliers } = storeToRefs(session);

const currentTitle = computed(() => {
	const match = NAV_ITEMS.find((item) => item.name === route.name);
	return match ? match.label : "Supplier Portal";
});

const supplierLabel = computed(() => {
	if (!suppliers.value.length) return "FreightMas";
	return suppliers.value.map((s) => s.supplier_name || s.name).join(", ");
});

const today = new Date().toLocaleDateString(undefined, { weekday: "long", day: "2-digit", month: "short", year: "numeric" });
</script>
