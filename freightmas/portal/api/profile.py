# Client Portal session context.
#
# A www/ page has no window.frappe.session the way a Desk Page does (that
# comes from desk.html's boot JS, which portal users never load), so the
# frontend fetches its own user/customer context on mount instead.

import frappe

from freightmas.portal.security import check_portal_access, get_portal_customer_names, log_portal_access


@frappe.whitelist()
def get_profile():
	check_portal_access()
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			frappe._("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)

	full_name = frappe.db.get_value("User", frappe.session.user, "full_name")
	customer_rows = frappe.get_all(
		"Customer", filters={"name": ["in", customers]}, fields=["name", "customer_name"]
	)

	log_portal_access("view_profile")

	return {
		"user": frappe.session.user,
		"full_name": full_name,
		"customers": customer_rows,
	}


@frappe.whitelist(methods=["POST"])
def logout():
	"""End the portal session. Frappe's built-in /api/method/logout rejects GET
	requests; the SPA must POST here (or to frappe.handler.logout) instead."""
	if frappe.session.user and frappe.session.user != "Guest":
		frappe.local.login_manager.logout()
		frappe.db.commit()
	return {"redirect_to": "/login?redirect-to=/client-portal"}
