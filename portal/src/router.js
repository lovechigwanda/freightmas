import { createRouter, createWebHashHistory } from "vue-router";

import DashboardView from "./views/DashboardView.vue";
import ShipmentsListView from "./views/ShipmentsListView.vue";
import ShipmentDetailView from "./views/ShipmentDetailView.vue";
import InvoicesListView from "./views/InvoicesListView.vue";
import InvoiceDetailView from "./views/InvoiceDetailView.vue";
import QuotationsListView from "./views/QuotationsListView.vue";
import QuotationDetailView from "./views/QuotationDetailView.vue";

// Static nav list drives both the sidebar and the router, same pattern as
// dashboard/src/router.js.
export const NAV_ITEMS = [
	{ path: "/", name: "dashboard", label: "Dashboard", icon: "dashboard", ready: true },
	{ path: "/shipments", name: "shipments", label: "Shipments", icon: "shipments", ready: true },
	{ path: "/quotations", name: "quotations", label: "Quotations", icon: "quotations", ready: true },
	{ path: "/invoices", name: "invoices", label: "Invoices", icon: "invoices", ready: true },
];

const routes = [
	{ path: "/", name: "dashboard", component: DashboardView },
	{ path: "/shipments", name: "shipments", component: ShipmentsListView },
	{ path: "/shipments/:id", name: "shipment-detail", component: ShipmentDetailView, props: true },
	{ path: "/quotations", name: "quotations", component: QuotationsListView },
	{
		path: "/quotations/:quotationName",
		name: "quotation-detail",
		component: QuotationDetailView,
		props: true,
	},
	{ path: "/invoices", name: "invoices", component: InvoicesListView },
	{
		path: "/invoices/:invoiceName",
		name: "invoice-detail",
		component: InvoiceDetailView,
		props: true,
	},
];

export default createRouter({
	history: createWebHashHistory(),
	routes,
});
