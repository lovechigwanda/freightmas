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

	// The Command Center brings its own sidebar/nav (see dashboard/src/shell),
	// so hide Desk's chrome around it: the page-head breadcrumb bar and the
	// global workspace sidebar. Scoped to this page's route so it reverts
	// automatically when navigating elsewhere in Desk.
	if (!document.getElementById("freightmas-command-center-chrome-css")) {
		$(
			`<style id="freightmas-command-center-chrome-css">
				body[data-route="freightmas-command-center"] .page-head,
				body[data-route="freightmas-command-center"] .body-sidebar-container,
				body[data-route="freightmas-command-center"] .body-sidebar-placeholder {
					display: none !important;
				}
			</style>`
		).appendTo("head");
	}

	const $mount = $('<div id="freightmas-command-center-app"></div>').appendTo(page.main);

	// The bundle is emitted with fixed filenames (dashboard.js/.css) so this
	// controller can reference them, but that means the browser + frappe.require
	// cache them by URL and can serve a stale bundle after a rebuild/deploy.
	// Append a cache-busting query so a new release is always fetched fresh:
	// in developer mode bust on every load; otherwise key on the bundle's own
	// mtime (set via the boot_session hook in freightmas/boot.py), which
	// changes automatically on every real deploy - no manual step required.
	const v = frappe.boot.developer_mode
		? Date.now()
		: frappe.boot.freightmas_dashboard_asset_version || "1";

	// frappe.require() can hang silently here: its AssetManager resolves
	// script/link onerror the same as onload "for backward compatibility",
	// so a stuck load_promises Promise.all never settles and never rejects
	// either - no console error, just a permanently blank page. Load the
	// two assets ourselves instead of going through that machinery.
	function load_asset(url) {
		return new Promise((resolve, reject) => {
			const is_css = url.split("?")[0].endsWith(".css");
			const el = is_css
				? Object.assign(document.createElement("link"), { rel: "stylesheet", href: url })
				: Object.assign(document.createElement("script"), { src: url });
			el.onload = () => resolve();
			el.onerror = () => reject(new Error(`Failed to load ${url}`));
			document.head.appendChild(el);
		});
	}

	load_asset(`/assets/freightmas/dashboard/dashboard.css?v=${v}`)
		.then(() => load_asset(`/assets/freightmas/dashboard/dashboard.js?v=${v}`))
		.then(() => {
			if (window.mountFreightMasDashboard) {
				window.mountFreightMasDashboard("#freightmas-command-center-app");
			} else {
				$mount.html(
					'<div style="padding: 24px; color: #d03e3e;">Command Center bundle failed to load. Run the frontend build (npm run build in the dashboard/ project) and reload.</div>'
				);
			}
		})
		.catch((err) => {
			$mount.html(
				`<div style="padding: 24px; color: #d03e3e;">Command Center bundle failed to load: ${frappe.utils.escape_html(err.message)}</div>`
			);
		});
};
