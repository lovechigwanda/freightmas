# Client Portal session context.
#
# A www/ page has no window.frappe.session the way a Desk Page does (that
# comes from desk.html's boot JS, which portal users never load), so the
# frontend fetches its own user/customer context on mount instead.

import frappe

from freightmas.portal.security import check_portal_access, get_portal_customer_names, log_portal_access
from freightmas.utils.company_branding import read_company_logo_bytes

PORTAL_LOGO_METHOD = "/api/method/freightmas.portal.api.profile.get_company_logo"


def _get_default_company_branding():
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		return {"company_name": "FreightMas", "logo": None}

	info = frappe.db.get_value(
		"Company",
		company,
		["company_name", "company_logo"],
		as_dict=True,
	) or {}
	logo = info.get("company_logo")
	return {
		"company_name": info.get("company_name") or company,
		"logo": PORTAL_LOGO_METHOD if logo else None,
	}


@frappe.whitelist()
def get_company_logo():
	"""Stream the default company logo for portal users (private files are not web-accessible)."""
	check_portal_access()

	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		frappe.throw(frappe._("Company logo not found."), frappe.DoesNotExistError)

	result = read_company_logo_bytes(company)
	if not result:
		frappe.throw(frappe._("Company logo not found."), frappe.DoesNotExistError)

	content, content_type, filename = result
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = content
	frappe.local.response.type = "binary"
	frappe.local.response["Content-Type"] = content_type

	log_portal_access("view_company_logo")


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
		"branding": _get_default_company_branding(),
	}


@frappe.whitelist(methods=["POST"])
def logout():
	"""End the portal session. Frappe's built-in /api/method/logout rejects GET
	requests; the SPA must POST here (or to frappe.handler.logout) instead."""
	if frappe.session.user and frappe.session.user != "Guest":
		frappe.local.login_manager.logout()
		frappe.db.commit()
	return {"redirect_to": "/login?redirect-to=/client-portal"}
