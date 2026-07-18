// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// Thin Desk Page shell - all real UI lives in the separately built Vue 3 SPA
// (see /dashboard in the app repo). This controller only mounts the built
// bundle into the page body; no business logic or data rendering happens here.
// The bundle now contains the full multi-module Command Center (sidebar +
// router), not just Forwarding - see dashboard/src/router.js for the module
// list.

frappe.pages["freightmas-command-center"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("FreightMas Command Center"),
		single_column: true,
	});

	page.main.css({ padding: 0, margin: 0, "max-width": "none" });

	const $mount = $('<div id="freightmas-command-center-app"></div>').appendTo(page.main);

	frappe.require([
		"/assets/freightmas/dashboard/dashboard.css",
		"/assets/freightmas/dashboard/dashboard.js",
	]).then(() => {
		if (window.mountFreightMasDashboard) {
			window.mountFreightMasDashboard("#freightmas-command-center-app");
		} else {
			$mount.html(
				'<div style="padding: 24px; color: #d03e3e;">Command Center bundle failed to load. Run the frontend build (npm run build in the dashboard/ project) and reload.</div>'
			);
		}
	});
};
