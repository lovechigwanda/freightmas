import { createRouter, createWebHashHistory } from "vue-router";

import DashboardView from "./views/DashboardView.vue";
import JobsListView from "./views/JobsListView.vue";
import JobDetailView from "./views/JobDetailView.vue";
import InvoicesListView from "./views/InvoicesListView.vue";
import InvoiceDetailView from "./views/InvoiceDetailView.vue";
import ComingSoonView from "./views/ComingSoonView.vue";

// Static nav list drives both the sidebar and the router, same pattern as
// portal/src/router.js. Profile renders a placeholder until a later phase
// adds its own view.
export const NAV_ITEMS = [
	{ path: "/", name: "dashboard", label: "Dashboard", icon: "dashboard", ready: true },
	{ path: "/jobs", name: "jobs", label: "My Jobs", icon: "jobs", ready: true },
	{ path: "/invoices", name: "invoices", label: "Invoices", icon: "invoices", ready: true },
	{ path: "/profile", name: "profile", label: "Profile", icon: "profile", ready: false },
];

const routes = [
	{ path: "/", name: "dashboard", component: DashboardView },
	{ path: "/jobs", name: "jobs", component: JobsListView },
	{ path: "/jobs/:jobDoctype/:jobName", name: "job-detail", component: JobDetailView, props: true },
	{ path: "/invoices", name: "invoices", component: InvoicesListView },
	{ path: "/invoices/:invoiceName", name: "invoice-detail", component: InvoiceDetailView, props: true },
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
