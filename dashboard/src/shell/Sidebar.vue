<template>
	<aside class="cc-sidebar">
		<div class="cc-sidebar-brand">
			<img v-if="branding.logo" :src="branding.logo" :alt="branding.company_name" />
			<div v-else class="cc-sidebar-brand-fallback">{{ brandInitials }}</div>
			<div class="cc-sidebar-brand-text">
				<div class="cc-sidebar-brand-name">{{ branding.company_name || "FreightMas" }}</div>
				<div class="cc-sidebar-brand-sub">Command Center</div>
			</div>
		</div>

		<nav class="cc-nav">
			<div class="cc-nav-section">Modules</div>
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

		<a class="cc-sidebar-foot" href="/app" title="Back to Frappe Desk">
			<div class="cc-sidebar-foot-avatar">{{ userInitials }}</div>
			<div class="cc-sidebar-foot-text">
				<div class="cc-sidebar-foot-name">{{ userName }}</div>
				<div class="cc-sidebar-foot-role">Back to Desk</div>
			</div>
		</a>
	</aside>
</template>

<script setup>
import { computed } from "vue";
import { initials } from "../format";
import { NAV_ICONS } from "../icons";

const props = defineProps({
	items: { type: Array, required: true },
	branding: { type: Object, default: () => ({}) },
});

const brandInitials = computed(() => initials(props.branding.company_name));

const userName = computed(() => window.frappe?.session?.user_fullname || window.frappe?.session?.user || "User");
const userInitials = computed(() => initials(userName.value));
</script>
