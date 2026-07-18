<template>
	<div class="cc-app">
		<Sidebar :items="navItems" :branding="branding" />
		<div class="cc-main">
			<TopBar :branding="branding" />
			<div class="cc-content">
				<router-view />
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { api } from "./modules/overview/api";
import { NAV_ITEMS } from "./router";
import Sidebar from "./shell/Sidebar.vue";
import TopBar from "./shell/TopBar.vue";

const navItems = NAV_ITEMS;
const branding = ref({});

onMounted(async () => {
	try {
		branding.value = await api.getBranding();
	} catch (e) {
		branding.value = { company_name: "FreightMas" };
	}
});
</script>

