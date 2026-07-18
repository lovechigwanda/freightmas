import { createRouter, createWebHashHistory } from "vue-router";

import CommandCenterOverview from "./modules/overview/CommandCenterOverview.vue";
import ForwardingModule from "./modules/forwarding/ForwardingModule.vue";
import ClearingModule from "./modules/clearing/ClearingModule.vue";
import ComingSoonView from "./modules/placeholder/ComingSoonView.vue";

// Static nav list drives both the sidebar and the router - add a real
// `component` here (instead of ComingSoonView) as each module's dashboard
// gets built out.
// `icon` is a lookup key into NAV_ICONS (see icons.js), not the icon itself -
// keeps this list framework-agnostic and easy to scan.
export const NAV_ITEMS = [
	{ path: "/", name: "overview", label: "Overview", icon: "overview", ready: true },
	{ path: "/forwarding", name: "forwarding", label: "Forwarding", icon: "forwarding", ready: true },
	{ path: "/clearing", name: "clearing", label: "Clearing", icon: "clearing", ready: true },
	{ path: "/border-clearing", name: "border-clearing", label: "Border Clearing", icon: "border-clearing", ready: false },
	{ path: "/road-freight", name: "road-freight", label: "Road Freight", icon: "road-freight", ready: false },
	{ path: "/trucking", name: "trucking", label: "Trucking", icon: "trucking", ready: false },
	{ path: "/warehouse", name: "warehouse", label: "Warehouse", icon: "warehouse", ready: false },
	{ path: "/invoicing", name: "invoicing", label: "Invoicing", icon: "invoicing", ready: false },
];

const routes = NAV_ITEMS.map((item) => {
	if (item.name === "overview") {
		return { path: item.path, name: item.name, component: CommandCenterOverview };
	}
	if (item.name === "forwarding") {
		return { path: item.path, name: item.name, component: ForwardingModule };
	}
	if (item.name === "clearing") {
		return { path: item.path, name: item.name, component: ClearingModule };
	}
	return {
		path: item.path,
		name: item.name,
		component: ComingSoonView,
		props: { moduleName: item.label, icon: item.icon },
	};
});

export default createRouter({
	history: createWebHashHistory(),
	routes,
});
