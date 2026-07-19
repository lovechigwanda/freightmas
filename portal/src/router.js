import { createRouter, createWebHashHistory } from "vue-router";

import DashboardView from "./views/DashboardView.vue";
import ShipmentsListView from "./views/ShipmentsListView.vue";
import ShipmentDetailView from "./views/ShipmentDetailView.vue";
import ComingSoonView from "./views/ComingSoonView.vue";

// Static nav list drives both the sidebar and the router, same pattern as
// dashboard/src/router.js. Invoices/Payments/Profile render a placeholder
// until Phase 2/3 add their API + views.
export const NAV_ITEMS = [
	{ path: "/", name: "dashboard", label: "Dashboard", icon: "dashboard", ready: true },
	{ path: "/shipments", name: "shipments", label: "Shipments", icon: "shipments", ready: true },
	{ path: "/invoices", name: "invoices", label: "Invoices", icon: "invoices", ready: false },
	{ path: "/payments", name: "payments", label: "Payments", icon: "payments", ready: false },
	{ path: "/profile", name: "profile", label: "Profile", icon: "profile", ready: false },
];

const routes = [
	{ path: "/", name: "dashboard", component: DashboardView },
	{ path: "/shipments", name: "shipments", component: ShipmentsListView },
	{ path: "/shipments/:id", name: "shipment-detail", component: ShipmentDetailView, props: true },
	...NAV_ITEMS.filter((item) => !item.ready && item.name !== "dashboard").map((item) => ({
		path: item.path,
		name: item.name,
		component: ComingSoonView,
		props: { moduleName: item.label, icon: item.icon },
	})),
];

export default createRouter({
	history: createWebHashHistory(),
	routes,
});
