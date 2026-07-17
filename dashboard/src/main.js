import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";

function mount(selector) {
	const el = document.querySelector(selector);
	if (!el) return;
	createApp(App).mount(el);
}

// Called by the Frappe Desk Page controller once the built bundle loads.
window.mountShipmentDashboard = mount;

// Standalone dev server (npm run dev) - auto-mount into #app.
if (import.meta.env.DEV) {
	mount("#app");
}
