import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import { PALETTES, DEFAULT_THEME_ID, paletteFor } from "../theme/palettes";
import { setActivePalette } from "../format";

// Shared with Command Center (`fm_cc_theme`) so the user's theme choice
// carries across FreightMas frontends on the same browser.
const STORAGE_KEY = "fm_cc_theme";

export const THEMES = [
	{ id: "light", label: "Light", group: "Light", swatch: { bg: "#ffffff", accent: "#4f46e5" } },
	{ id: "green-light", label: "Green (Light)", group: "Light", swatch: { bg: "#ffffff", accent: "#0f7a52" } },
	{ id: "dark-terminal", label: "Dark Terminal", group: "Dark", swatch: { bg: "#0d1219", accent: "#f5a623" } },
	{ id: "gleinna", label: "Gleinna Brand", group: "Dark", swatch: { bg: "#221a4d", accent: "#f5921e" } },
	{ id: "green-dark", label: "Green (Dark)", group: "Dark", swatch: { bg: "#121b17", accent: "#22c55e" } },
	{ id: "meridian", label: "Meridian", group: "Dark", swatch: { bg: "#0e1526", accent: "#38bdf8" } },
];

function loadPersisted() {
	if (typeof window === "undefined") return DEFAULT_THEME_ID;
	try {
		const saved = window.localStorage.getItem(STORAGE_KEY);
		return saved && PALETTES[saved] ? saved : DEFAULT_THEME_ID;
	} catch (e) {
		return DEFAULT_THEME_ID;
	}
}

function applyThemeId(id) {
	if (typeof document !== "undefined") {
		document.documentElement.setAttribute("data-cc-theme", id);
	}
	setActivePalette(paletteFor(id));
}

applyThemeId(loadPersisted());

export const useThemeStore = defineStore("theme", () => {
	const themeId = ref(loadPersisted());
	const palette = computed(() => paletteFor(themeId.value));

	function setTheme(id) {
		if (!PALETTES[id]) return;
		themeId.value = id;
	}

	watch(themeId, (id) => {
		applyThemeId(id);
		if (typeof window !== "undefined") {
			try {
				window.localStorage.setItem(STORAGE_KEY, id);
			} catch (e) {
				/* private mode */
			}
		}
	});

	return { themeId, palette, themes: THEMES, setTheme };
});
