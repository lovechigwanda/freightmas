# Supplier Portal session context.
#
# A www/ page has no window.frappe.session the way a Desk Page does (that
# comes from desk.html's boot JS, which portal users never load), so the
# frontend fetches its own user/supplier context on mount instead.

import frappe

from freightmas.portal.security import (
	SUPPLIER_PORTAL_ROLE,
	check_portal_access,
	get_portal_supplier_names,
	log_portal_access,
)


@frappe.whitelist()
def get_profile():
	check_portal_access(role=SUPPLIER_PORTAL_ROLE)
	suppliers = get_portal_supplier_names()
	if not suppliers:
		frappe.throw(
			frappe._("Your account is not linked to a supplier profile. Contact your account manager."),
			frappe.PermissionError,
		)

	full_name = frappe.db.get_value("User", frappe.session.user, "full_name")
	supplier_rows = frappe.get_all(
		"Supplier", filters={"name": ["in", suppliers]}, fields=["name", "supplier_name"]
	)

	log_portal_access("view_profile", party_type="Supplier", party=suppliers[0] if len(suppliers) == 1 else None)

	return {
		"user": frappe.session.user,
		"full_name": full_name,
		"suppliers": supplier_rows,
	}
