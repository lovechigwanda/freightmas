<template>
	<div class="cc-theme" ref="root">
		<button
			class="cc-theme-btn"
			type="button"
			:aria-expanded="open"
			aria-haspopup="menu"
			title="Change theme"
			@click.stop="open = !open"
		>
			<Palette :size="16" stroke-width="2" />
		</button>

		<div v-if="open" class="cc-theme-menu" role="menu">
			<div class="cc-theme-menu-head">Theme</div>
			<button
				v-for="t in themes"
				:key="t.id"
				class="cc-theme-option"
				:class="{ active: t.id === themeId }"
				type="button"
				role="menuitemradio"
				:aria-checked="t.id === themeId"
				@click="choose(t.id)"
			>
				<span class="cc-theme-swatch" :style="{ background: t.swatch.bg }">
					<span class="cc-theme-swatch-dot" :style="{ background: t.swatch.accent }"></span>
				</span>
				<span class="cc-theme-option-label">{{ t.label }}</span>
				<Check v-if="t.id === themeId" :size="15" stroke-width="2.5" class="cc-theme-check" />
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import { Palette, Check } from "@lucide/vue";
import { useThemeStore, THEMES } from "../stores/theme";

const store = useThemeStore();
const { themeId } = storeToRefs(store);
const themes = THEMES;

const open = ref(false);
const root = ref(null);

function choose(id) {
	store.setTheme(id);
	open.value = false;
}

// Close on any outside click or Escape while the menu is open.
function onDocClick(e) {
	if (root.value && !root.value.contains(e.target)) open.value = false;
}
function onKey(e) {
	if (e.key === "Escape") open.value = false;
}

// Attach the document listeners only while the menu is open.
watch(open, (isOpen) => {
	if (typeof document === "undefined") return;
	if (isOpen) {
		document.addEventListener("click", onDocClick);
		document.addEventListener("keydown", onKey);
	} else {
		document.removeEventListener("click", onDocClick);
		document.removeEventListener("keydown", onKey);
	}
});

onBeforeUnmount(() => {
	if (typeof document === "undefined") return;
	document.removeEventListener("click", onDocClick);
	document.removeEventListener("keydown", onKey);
});
</script>

<style scoped>
.cc-theme {
	position: relative;
	flex-shrink: 0;
}

.cc-theme-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 32px;
	height: 32px;
	border-radius: 8px;
	border: 1px solid var(--cc-sidebar-border);
	background: var(--cc-sidebar-hover);
	color: var(--cc-sidebar-text);
	cursor: pointer;
	transition: color 0.12s ease, border-color 0.12s ease;
}

.cc-theme-btn:hover,
.cc-theme-btn[aria-expanded="true"] {
	color: var(--cc-sidebar-text-active);
	border-color: var(--cc-nav-accent);
}

.cc-theme-menu {
	position: absolute;
	bottom: calc(100% + 10px);
	right: 0;
	width: 216px;
	background: var(--cc-sidebar-bg-elevated);
	border: 1px solid var(--cc-sidebar-border);
	border-radius: 12px;
	padding: 6px;
	box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
	z-index: 50;
}

.cc-theme-menu-head {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.07em;
	color: var(--cc-sidebar-text-muted);
	padding: 6px 8px 4px;
}

.cc-theme-option {
	display: flex;
	align-items: center;
	gap: 10px;
	width: 100%;
	padding: 8px;
	border: none;
	background: transparent;
	border-radius: 8px;
	color: var(--cc-sidebar-text);
	font-size: 13px;
	font-family: inherit;
	text-align: left;
	cursor: pointer;
	transition: background 0.12s ease, color 0.12s ease;
}

.cc-theme-option:hover {
	background: var(--cc-sidebar-hover);
	color: var(--cc-sidebar-text-active);
}

.cc-theme-option.active {
	color: var(--cc-sidebar-text-active);
	font-weight: 600;
}

.cc-theme-swatch {
	position: relative;
	width: 20px;
	height: 20px;
	border-radius: 6px;
	border: 1px solid var(--cc-sidebar-border);
	flex-shrink: 0;
}

.cc-theme-swatch-dot {
	position: absolute;
	right: 3px;
	bottom: 3px;
	width: 8px;
	height: 8px;
	border-radius: 999px;
}

.cc-theme-option-label {
	flex: 1;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.cc-theme-check {
	color: var(--cc-nav-accent);
	flex-shrink: 0;
}
</style>
