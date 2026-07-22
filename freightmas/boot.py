import os

import frappe


def boot_session(bootinfo):
	# The Command Center Desk Page loads its Vue bundle under fixed filenames
	# (dashboard.js/.css), so the browser has no natural cue that a rebuild
	# happened. Bust the cache with the bundle's own mtime, which changes on
	# every real deploy - mirrors the scheme www/client-portal/index.py and
	# www/supplier-portal/index.py use for the same reason.
	bundle_path = frappe.get_app_path("freightmas", "public", "dashboard", "dashboard.js")
	try:
		version = str(int(os.path.getmtime(bundle_path)))
	except OSError:
		version = frappe.utils.now_datetime().strftime("%Y%m%d%H%M%S")

	bootinfo["freightmas_dashboard_asset_version"] = version
