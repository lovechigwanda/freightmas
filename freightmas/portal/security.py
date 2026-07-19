# Client Portal security primitives.
#
# This module is the ONLY gate for customer-facing data access. It is
# deliberately kept separate from freightmas.utils.permissions (the
# internal-Desk gate) so the internal-staff and customer-portal trust
# boundaries can never be confused for one another. Customer Portal User
# holds zero DocType permissions anywhere in the system: every read a
# portal user is allowed to make goes through an explicit check here.

import frappe
from frappe import _

PORTAL_ROLE = "Customer Portal User"

# Roles core Frappe assigns to every user unconditionally. "All" carries
# desk_access=1 purely so DocType permission rules can target "everyone" -
# not because holding it implies actual Desk/staff status. Never treat
# these as evidence of a Desk-access account.
UNIVERSAL_ROLES = frozenset({"All", "Guest"})


def check_portal_access():
	"""Verify the current session is a provisioned, desk-locked portal user.

	Re-checked on every request rather than trusted from provisioning time,
	in case a future manual edit or migration bug reintroduces a bad state.

	Raises:
		frappe.PermissionError: if the user is a Guest, not a Website User,
			lacks the Customer Portal User role, or holds any role with
			Desk access.
	"""
	user = frappe.session.user

	if user == "Guest":
		frappe.throw(_("Please login to access the client portal."), frappe.PermissionError)

	user_type = frappe.db.get_value("User", user, "user_type")
	if user_type != "Website User":
		frappe.throw(_("You do not have permission to access the client portal."), frappe.PermissionError)

	roles = frappe.get_roles(user)

	if PORTAL_ROLE not in roles:
		frappe.throw(_("You do not have permission to access the client portal."), frappe.PermissionError)

	non_universal_roles = set(roles) - UNIVERSAL_ROLES
	has_desk_role = non_universal_roles and frappe.get_all(
		"Role",
		filters={"name": ["in", list(non_universal_roles)], "desk_access": 1},
		limit=1,
	)
	if has_desk_role:
		frappe.throw(_("You do not have permission to access the client portal."), frappe.PermissionError)


def get_portal_customer_names():
	"""Resolve the logged-in portal user to their entitled Customer(s).

	Returns:
		list[str]: Customer names the caller's Contact is linked to. Empty
			if there is no Contact, or the Contact has no Customer links.
			Callers MUST treat an empty list as "no access" and never as
			"unfiltered access".
	"""
	user = frappe.session.user

	contact_name = frappe.db.get_value("Contact", {"user": user}, "name")
	if not contact_name:
		return []

	customers = frappe.get_all(
		"Dynamic Link",
		filters={
			"parenttype": "Contact",
			"parent": contact_name,
			"link_doctype": "Customer",
		},
		pluck="link_name",
	)
	return list(dict.fromkeys(customers))


def assert_customer_scope(doctype, docname, customer_fieldname="customer"):
	"""Verify docname belongs to one of the logged-in user's Customers.

	Loads only the customer field before anything else, so a scope failure
	never leaks other fields on the document to the caller.

	Returns:
		str: the matching Customer name (useful for audit logging).

	Raises:
		frappe.PermissionError: if docname does not exist, has no value in
			customer_fieldname, or belongs to a Customer the caller is not
			entitled to.
	"""
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(_("You do not have permission to view this record."), frappe.PermissionError)

	owner_customer = frappe.db.get_value(doctype, docname, customer_fieldname)
	if not owner_customer or owner_customer not in customers:
		frappe.throw(_("You do not have permission to view this record."), frappe.PermissionError)

	return owner_customer


def log_portal_access(action, doctype=None, docname=None, customer=None):
	"""Write an audit row for a portal action.

	Client Portal Access Log grants no permission to Customer Portal User
	(System Manager only), so the portal can never read or tamper with its
	own audit trail. Logging failures never block the underlying request.
	"""
	try:
		frappe.get_doc(
			{
				"doctype": "Client Portal Access Log",
				"user": frappe.session.user,
				"customer": customer,
				"action": action,
				"reference_doctype": doctype,
				"reference_name": docname,
				"ip_address": frappe.local.request_ip if getattr(frappe.local, "request_ip", None) else None,
				"timestamp": frappe.utils.now(),
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Client Portal Access Log Error")
