# Client/Supplier Portal security primitives.
#
# This module is the ONLY gate for customer- and supplier-facing data
# access. It is deliberately kept separate from freightmas.utils.permissions
# (the internal-Desk gate) so the internal-staff and portal trust boundaries
# can never be confused for one another. Portal roles hold zero DocType
# permissions anywhere in the system: every read a portal user is allowed to
# make goes through an explicit check here.

import frappe
from frappe import _

PORTAL_ROLE = "Customer Portal User"
CUSTOMER_PORTAL_ROLE = PORTAL_ROLE
SUPPLIER_PORTAL_ROLE = "Supplier Portal User"

# Roles core Frappe assigns to every user unconditionally. "All" carries
# desk_access=1 purely so DocType permission rules can target "everyone" -
# not because holding it implies actual Desk/staff status. Never treat
# these as evidence of a Desk-access account.
UNIVERSAL_ROLES = frozenset({"All", "Guest"})


def check_portal_access(role=PORTAL_ROLE):
	"""Verify the current session is a provisioned, desk-locked portal user.

	Re-checked on every request rather than trusted from provisioning time,
	in case a future manual edit or migration bug reintroduces a bad state.

	Args:
		role: the portal role the caller must hold (defaults to the
			Customer Portal role, so every existing call site is unaffected).

	Raises:
		frappe.PermissionError: if the user is a Guest, not a Website User,
			lacks the given portal role, or holds any role with Desk access.
	"""
	user = frappe.session.user

	if user == "Guest":
		frappe.throw(_("Please login to access this portal."), frappe.PermissionError)

	user_type = frappe.db.get_value("User", user, "user_type")
	if user_type != "Website User":
		frappe.throw(_("You do not have permission to access this portal."), frappe.PermissionError)

	roles = frappe.get_roles(user)

	if role not in roles:
		frappe.throw(_("You do not have permission to access this portal."), frappe.PermissionError)

	non_universal_roles = set(roles) - UNIVERSAL_ROLES
	has_desk_role = non_universal_roles and frappe.get_all(
		"Role",
		filters={"name": ["in", list(non_universal_roles)], "desk_access": 1},
		limit=1,
	)
	if has_desk_role:
		frappe.throw(_("You do not have permission to access this portal."), frappe.PermissionError)


def get_portal_party_names(link_doctype):
	"""Resolve the logged-in portal user to their entitled party record(s).

	Args:
		link_doctype: "Customer" or "Supplier" - which Dynamic Link type on
			the caller's Contact to resolve.

	Returns:
		list[str]: party names the caller's Contact is linked to. Empty if
			there is no Contact, or the Contact has no such links. Callers
			MUST treat an empty list as "no access" and never as "unfiltered
			access".
	"""
	user = frappe.session.user

	contact_name = frappe.db.get_value("Contact", {"user": user}, "name")
	if not contact_name:
		return []

	names = frappe.get_all(
		"Dynamic Link",
		filters={
			"parenttype": "Contact",
			"parent": contact_name,
			"link_doctype": link_doctype,
		},
		pluck="link_name",
	)
	return list(dict.fromkeys(names))


def get_portal_customer_names():
	"""Resolve the logged-in portal user to their entitled Customer(s)."""
	return get_portal_party_names("Customer")


def get_portal_supplier_names():
	"""Resolve the logged-in portal user to their entitled Supplier(s)."""
	return get_portal_party_names("Supplier")


def assert_party_scope(doctype, docname, party_fieldname, party_names):
	"""Verify docname belongs to one of the given party names.

	Loads only the scope field before anything else, so a scope failure
	never leaks other fields on the document to the caller.

	Returns:
		str: the matching party name (useful for audit logging).

	Raises:
		frappe.PermissionError: if party_names is empty, docname does not
			exist, has no value in party_fieldname, or belongs to a party
			the caller is not entitled to.
	"""
	if not party_names:
		frappe.throw(_("You do not have permission to view this record."), frappe.PermissionError)

	owner_party = frappe.db.get_value(doctype, docname, party_fieldname)
	if not owner_party or owner_party not in party_names:
		frappe.throw(_("You do not have permission to view this record."), frappe.PermissionError)

	return owner_party


def assert_customer_scope(doctype, docname, customer_fieldname="customer"):
	"""Verify docname belongs to one of the logged-in user's Customers."""
	return assert_party_scope(doctype, docname, customer_fieldname, get_portal_customer_names())


def assert_supplier_scope(doctype, docname, supplier_fieldname="supplier"):
	"""Verify docname belongs to one of the logged-in user's Suppliers."""
	return assert_party_scope(doctype, docname, supplier_fieldname, get_portal_supplier_names())


def log_portal_access(action, doctype=None, docname=None, customer=None, party_type=None, party=None):
	"""Write an audit row for a portal action.

	Client Portal Access Log grants no permission to any portal role
	(System Manager only), so a portal user can never read or tamper with
	its own audit trail. Logging failures never block the underlying
	request.

	Args:
		customer: legacy kwarg, kept so existing Customer-portal call sites
			are unaffected. Equivalent to party_type="Customer", party=customer.
		party_type / party: "Customer"/"Supplier" and the resolved party
			name - preferred for new call sites.
	"""
	if party_type is None and customer is not None:
		party_type, party = "Customer", customer

	try:
		frappe.get_doc(
			{
				"doctype": "Client Portal Access Log",
				"user": frappe.session.user,
				"customer": party if party_type == "Customer" else None,
				"party_type": party_type,
				"party": party,
				"action": action,
				"reference_doctype": doctype,
				"reference_name": docname,
				"ip_address": frappe.local.request_ip if getattr(frappe.local, "request_ip", None) else None,
				"timestamp": frappe.utils.now(),
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Client Portal Access Log Error")
