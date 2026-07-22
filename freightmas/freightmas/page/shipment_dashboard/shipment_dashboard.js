// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// Thin Desk Page shell - all real UI lives in the separately built Vue 3 SPA
// (see /dashboard in the app repo). This controller only mounts the built
// bundle into the page body; no business logic or data rendering happens here.

frappe.pages["shipment-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Shipment Dashboard"),
		single_column: true,
	});

	page.main.css({ padding: 0, margin: 0, "max-width": "none" });

	const $mount = $('<div id="shipment-dashboard-app"></div>').appendTo(page.main);

	// Cache-bust the fixed-name bundle so a rebuild/deploy is fetched fresh
	// (see freightmas_command_center.js for the rationale).
	const v = frappe.boot.developer_mode
		? Date.now()
		: frappe.boot.freightmas_dashboard_asset_version || "1";

	frappe.require([
		`/assets/freightmas/dashboard/dashboard.css?v=${v}`,
		`/assets/freightmas/dashboard/dashboard.js?v=${v}`,
	]).then(() => {
		if (window.mountShipmentDashboard) {
			window.mountShipmentDashboard("#shipment-dashboard-app");
		} else {
			$mount.html(
				'<div style="padding: 24px; color: #d03e3e;">Shipment Dashboard bundle failed to load. Run the frontend build (npm run build in the dashboard/ project) and reload.</div>'
			);
		}
	});
};
