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
import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import { NAV_ITEMS } from "./router";
import { useSessionStore } from "./stores/session";
import Sidebar from "./shell/Sidebar.vue";
import TopBar from "./shell/TopBar.vue";

const navItems = NAV_ITEMS;

// Branding is fetched once here and shared via the session store; the shell
// components read it from the store rather than each fetching their own.
const session = useSessionStore();
const { branding } = storeToRefs(session);

onMounted(() => session.loadBranding());
</script>

