<template>
	<div class="cc-app">
		<Sidebar :items="navItems" />
		<div class="cc-main">
			<TopBar />
			<div class="cc-content">
				<router-view />
			</div>
		</div>
	</div>
</template>

<script setup>
import { onMounted } from "vue";
import { NAV_ITEMS } from "./router";
import { useSessionStore } from "./stores/session";
import Sidebar from "./shell/Sidebar.vue";
import TopBar from "./shell/TopBar.vue";

const navItems = NAV_ITEMS;

const session = useSessionStore();
onMounted(() => session.load());
</script>
