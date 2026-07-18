import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./style.css";

function mount(selector) {
	const el = document.querySelector(selector);
	if (!el) return;
	createApp(App).use(createPinia()).use(router).mount(el);
}

// Called by the Frappe Desk Page controller once the built bundle loads.
window.mountFreightMasDashboard = mount;
// Back-compat alias for the original single-module Shipment Dashboard page.
window.mountShipmentDashboard = mount;

// Standalone dev server (npm run dev) - auto-mount into #app.
if (import.meta.env.DEV) {
	mount("#app");
}
