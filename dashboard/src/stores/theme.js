import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import { PALETTES, DEFAULT_THEME_ID, paletteFor } from "../theme/palettes";
import { setActivePalette } from "../format";

// User-selectable Command Center theme. The choice is a personal preference, so
// it is persisted per-browser to localStorage (mirrors the sessionStorage idiom
// in stores/filters.js, using an `fm_cc_` key). Switching writes a
// `data-cc-theme` attribute on <html> which flips every CSS custom property (see
// themes.css); the JS chart palette (theme/palettes.js) is swapped in parallel
// for the canvas/SVG charts that don't follow the CSS cascade.

const STORAGE_KEY = "fm_cc_theme";

// The flat switcher list. Green is presented as two entries (light/dark) and
// Dark Terminal ships with its default amber accent - see the design handoffs.
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

// Reflect the id onto <html> and into the synchronous format.js palette mirror.
function applyThemeId(id) {
	if (typeof document !== "undefined") {
		document.documentElement.setAttribute("data-cc-theme", id);
	}
	setActivePalette(paletteFor(id));
}

// Applied once at module load so the correct theme is on <html> before Vue's
// first paint (no flash of the default light theme on reload).
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
				/* private mode / storage disabled - theme still applies this session */
			}
		}
	});

	return { themeId, palette, themes: THEMES, setTheme };
});
