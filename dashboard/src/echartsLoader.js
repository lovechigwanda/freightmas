// Lazy, tree-shaken ECharts loader. Everything here is pulled in via a single
// dynamic import() from Chart.vue, so ECharts lands in its OWN Rollup chunk
// (assets/dashboard-echartsLoader-*.js) and never bloats the always-loaded
// dashboard.js entry. Only the chart types / components the Command Center
// actually uses are registered, keeping the chunk small.
//
// ECharts is pure JS (no eval, no CDN fetch) so it is safe under Frappe Desk's
// Content-Security-Policy as a bundled asset.

import * as echarts from "echarts/core";
import { LineChart, BarChart, PieChart } from "echarts/charts";
import {
	GridComponent,
	TooltipComponent,
	LegendComponent,
	DatasetComponent,
	MarkLineComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

let registered = false;

function ensureRegistered() {
	if (registered) return;
	echarts.use([
		LineChart,
		BarChart,
		PieChart,
		GridComponent,
		TooltipComponent,
		LegendComponent,
		DatasetComponent,
		MarkLineComponent,
		CanvasRenderer,
	]);
	registered = true;
}

export function getECharts() {
	ensureRegistered();
	return echarts;
}
