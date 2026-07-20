<template>
	<aside class="cc-sidebar">
		<div class="cc-sidebar-brand">
			<div class="cc-sidebar-brand-fallback">FM</div>
			<div class="cc-sidebar-brand-text">
				<div class="cc-sidebar-brand-name">FreightMas</div>
				<div class="cc-sidebar-brand-sub">Supplier Portal</div>
			</div>
		</div>

		<nav class="cc-nav">
			<div class="cc-nav-section">Menu</div>
			<router-link
				v-for="item in items"
				:key="item.name"
				:to="item.path"
				class="cc-nav-item"
				active-class="active"
			>
				<span class="cc-nav-icon">
					<component :is="NAV_ICONS[item.icon]" :size="17" stroke-width="2" />
				</span>
				<span class="cc-nav-label">{{ item.label }}</span>
				<span v-if="!item.ready" class="cc-nav-soon">Soon</span>
			</router-link>
		</nav>

		<a class="cc-sidebar-foot" href="/api/method/logout" title="Log out">
			<div class="cc-sidebar-foot-avatar">{{ userInitials }}</div>
			<div class="cc-sidebar-foot-text">
				<div class="cc-sidebar-foot-name">{{ displayName }}</div>
				<div class="cc-sidebar-foot-role">Log out</div>
			</div>
		</a>
	</aside>
</template>

<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { initials } from "../format";
import { NAV_ICONS } from "../icons";
import { useSessionStore } from "../stores/session";

defineProps({
	items: { type: Array, required: true },
});

const session = useSessionStore();
const { fullName } = storeToRefs(session);

const displayName = computed(() => fullName.value || "Account");
const userInitials = computed(() => initials(displayName.value));
</script>
