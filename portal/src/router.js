import { createRouter, createWebHashHistory } from "vue-router";

import DashboardView from "./views/DashboardView.vue";
import ShipmentsListView from "./views/ShipmentsListView.vue";
import ShipmentDetailView from "./views/ShipmentDetailView.vue";
import InvoicesListView from "./views/InvoicesListView.vue";
import InvoiceDetailView from "./views/InvoiceDetailView.vue";
import ComingSoonView from "./views/ComingSoonView.vue";

// Static nav list drives both the sidebar and the router, same pattern as
// dashboard/src/router.js. Payments/Profile render a placeholder until a
// later phase adds their API + views; payment history now lives inside
// invoice detail, so there is no separate Payments screen for Phase 2.
export const NAV_ITEMS = [
	{ path: "/", name: "dashboard", label: "Dashboard", icon: "dashboard", ready: true },
	{ path: "/shipments", name: "shipments", label: "Shipments", icon: "shipments", ready: true },
	{ path: "/invoices", name: "invoices", label: "Invoices", icon: "invoices", ready: true },
	{ path: "/payments", name: "payments", label: "Payments", icon: "payments", ready: false },
	{ path: "/profile", name: "profile", label: "Profile", icon: "profile", ready: false },
];

const routes = [
	{ path: "/", name: "dashboard", component: DashboardView },
	{ path: "/shipments", name: "shipments", component: ShipmentsListView },
	{ path: "/shipments/:id", name: "shipment-detail", component: ShipmentDetailView, props: true },
	{ path: "/invoices", name: "invoices", component: InvoicesListView },
	{
		path: "/invoices/:invoiceName",
		name: "invoice-detail",
		component: InvoiceDetailView,
		props: true,
	},
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
