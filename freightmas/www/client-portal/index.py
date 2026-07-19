import os

import frappe

from freightmas.portal.security import check_portal_access

no_cache = 1


def _asset_version():
	# Fixed (non-hashed) bundle filenames mean the browser has no natural
	# cue that a new build exists - bust the cache with the built file's own
	# mtime, which changes exactly when `npm run build` last ran. Mirrors the
	# ?v= scheme freightmas_command_center.js uses for the same Desk Page
	# reason, just computed server-side since Jinja has no frappe.boot here.
	bundle_path = frappe.get_app_path("freightmas", "public", "portal", "portal.js")
	try:
		return str(int(os.path.getmtime(bundle_path)))
	except OSError:
		return frappe.utils.now_datetime().strftime("%Y%m%d%H%M%S")


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.flags.redirect_location = "/login?redirect-to=/client-portal"
		raise frappe.Redirect

	try:
		check_portal_access()
	except frappe.PermissionError:
		context.http_status_code = 403
		context.access_denied = True
		context.no_cache = 1
		return context

	context.access_denied = False
	context.no_cache = 1
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.asset_version = _asset_version()
	return context
