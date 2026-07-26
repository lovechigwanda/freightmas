// Per-theme JS colour palettes for the CHART layer.
//
// CSS-variable theming (see style.css / themes.css) recolours all HTML/DOM, but
// ECharts paints to a <canvas> and DonutChart/Sparkline take colours via props -
// none of those follow the CSS cascade. This module is the single source of
// truth for those JS-set colours, keyed by the same theme ids used for the
// `data-cc-theme` attribute. The theme store (stores/theme.js) selects the
// active entry; format.js mirrors it for its synchronous `statusColor`.

// Shared semantic status ramp per theme (job statuses in the module donuts) +
// the ECharts series/axis colours for the executive trend chart + KPI spark
// tones. Values mirror the design-handoff tokens for each theme.
export const PALETTES = {
	light: {
		series: { revenue: "#4f46e5", cost: "#d97706", margin: "#0d9488" },
		ramp: ["#4f46e5", "#0d9488", "#d97706", "#16a34a", "#dc2626", "#94a3b8", "#7c3aed", "#0891b2"],
		status: { Draft: "#94a3b8", "In Progress": "#4f46e5", Delivered: "#16a34a", Completed: "#0d9488", Closed: "#64748b", Cancelled: "#dc2626" },
		spark: { default: "#4f46e5", warn: "#d97706", danger: "#dc2626", good: "#16a34a" },
		chart: { axisLine: "#e2e8f0", axisLabel: "#64748b", splitLine: "#eef0f5", axisLabelFaint: "#94a3b8" },
	},
	"dark-terminal": {
		series: { revenue: "#f5a623", cost: "#f87171", margin: "#2dd4bf" },
		ramp: ["#f5a623", "#2dd4bf", "#a78bfa", "#34d399", "#f87171", "#8b96a8", "#22d3ee", "#fbbf24"],
		status: { Draft: "#8b96a8", "In Progress": "#f5a623", Delivered: "#34d399", Completed: "#2dd4bf", Closed: "#5c6579", Cancelled: "#f87171" },
		spark: { default: "#f5a623", warn: "#fbbf24", danger: "#f87171", good: "#34d399" },
		chart: { axisLine: "rgba(255,255,255,0.10)", axisLabel: "#8b96a8", splitLine: "rgba(255,255,255,0.06)", axisLabelFaint: "#5c6579" },
	},
	gleinna: {
		series: { revenue: "#f5921e", cost: "#ff6b6b", margin: "#8f86d1" },
		ramp: ["#f5921e", "#8f86d1", "#ffcf4d", "#34d399", "#ff6b6b", "#a79ddc", "#22d3ee", "#cfc9ec"],
		status: { Draft: "#a79ddc", "In Progress": "#f5921e", Delivered: "#34d399", Completed: "#8f86d1", Closed: "#8177ad", Cancelled: "#ff6b6b" },
		spark: { default: "#f5921e", warn: "#ffcf4d", danger: "#ff6b6b", good: "#34d399" },
		chart: { axisLine: "rgba(255,255,255,0.12)", axisLabel: "#a79ddc", splitLine: "rgba(255,255,255,0.07)", axisLabelFaint: "#8177ad" },
	},
	"green-light": {
		series: { revenue: "#0f7a52", cost: "#a3690f", margin: "#b98b3e" },
		ramp: ["#0f7a52", "#b98b3e", "#a3690f", "#16a34a", "#b3261e", "#8ea198", "#0b5c3d", "#5b6d63"],
		status: { Draft: "#8ea198", "In Progress": "#0f7a52", Delivered: "#16a34a", Completed: "#0b5c3d", Closed: "#5b6d63", Cancelled: "#b3261e" },
		spark: { default: "#0f7a52", warn: "#a3690f", danger: "#b3261e", good: "#16a34a" },
		chart: { axisLine: "#dde7e1", axisLabel: "#5b6d63", splitLine: "#eaf1ed", axisLabelFaint: "#8ea198" },
	},
	"green-dark": {
		series: { revenue: "#22c55e", cost: "#eab308", margin: "#d9b45f" },
		ramp: ["#22c55e", "#d9b45f", "#eab308", "#34d399", "#f87171", "#93a89c", "#15803d", "#5f746a"],
		status: { Draft: "#93a89c", "In Progress": "#22c55e", Delivered: "#34d399", Completed: "#15803d", Closed: "#5f746a", Cancelled: "#f87171" },
		spark: { default: "#22c55e", warn: "#eab308", danger: "#f87171", good: "#34d399" },
		chart: { axisLine: "rgba(255,255,255,0.10)", axisLabel: "#93a89c", splitLine: "rgba(255,255,255,0.06)", axisLabelFaint: "#5f746a" },
	},
	meridian: {
		series: { revenue: "#38bdf8", cost: "#f87171", margin: "#818cf8" },
		ramp: ["#38bdf8", "#818cf8", "#fbbf24", "#34d399", "#f87171", "#9aa8ca", "#22d3ee", "#3b82f6"],
		status: { Draft: "#9aa8ca", "In Progress": "#38bdf8", Delivered: "#34d399", Completed: "#818cf8", Closed: "#5a6a8f", Cancelled: "#f87171" },
		spark: { default: "#38bdf8", warn: "#fbbf24", danger: "#f87171", good: "#34d399" },
		chart: { axisLine: "rgba(255,255,255,0.10)", axisLabel: "#9aa8ca", splitLine: "rgba(255,255,255,0.06)", axisLabelFaint: "#5a6a8f" },
	},
};

export const DEFAULT_THEME_ID = "light";

export function paletteFor(id) {
	return PALETTES[id] || PALETTES[DEFAULT_THEME_ID];
}
