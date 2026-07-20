# Keeps Client/Supplier Portal accounts locked to Website User + the
# matching portal role, and forbids a portal login from ever doubling as a
# staff account.
#
# Hooked from hooks.py on Contact.validate and User.validate so the
# constraint holds however the linkage is created or edited: via a Contact
# form save, a direct User edit, or "Invite as User".
#
# A Contact may carry Dynamic Links to both a Customer and a Supplier (e.g.
# a broker who is legitimately both) - such a Contact's User gets both
# portal roles rather than being rejected.

import frappe
from frappe import _

from freightmas.portal.security import CUSTOMER_PORTAL_ROLE, SUPPLIER_PORTAL_ROLE, UNIVERSAL_ROLES

# link_doctype -> portal role granted when a Contact carries that link type.
PARTY_ROLE_MAP = {
	"Customer": CUSTOMER_PORTAL_ROLE,
	"Supplier": SUPPLIER_PORTAL_ROLE,
}


def sync_portal_user_on_contact_save(doc, method=None):
	"""Contact validate hook: enforce portal constraints on doc.user."""
	if not doc.user:
		return

	linked_types = {link.link_doctype for link in doc.links}
	portal_roles = [role for link_doctype, role in PARTY_ROLE_MAP.items() if link_doctype in linked_types]
	if not portal_roles:
		return

	user_doc = frappe.get_doc("User", doc.user)
	_apply_portal_constraints(user_doc, portal_roles)
	user_doc.save(ignore_permissions=True)


def enforce_portal_user_type(doc, method=None):
	"""User validate hook: re-apply portal constraints whenever the User
	record itself is edited (e.g. someone manually adds a Desk role)."""
	contact_name = frappe.db.get_value("Contact", {"user": doc.name}, "name")
	if not contact_name:
		return

	linked_types = set(
		frappe.get_all(
			"Dynamic Link",
			filters={"parenttype": "Contact", "parent": contact_name, "link_doctype": ["in", list(PARTY_ROLE_MAP)]},
			pluck="link_doctype",
		)
	)
	portal_roles = [role for link_doctype, role in PARTY_ROLE_MAP.items() if link_doctype in linked_types]
	if not portal_roles:
		return

	_apply_portal_constraints(doc, portal_roles)


def _apply_portal_constraints(user_doc, portal_roles):
	# user_type == "System User" is just the DocType field default for any
	# freshly created User, so it is not by itself evidence of a real staff
	# account. The meaningful signal is whether this user already holds a
	# Desk-access role - i.e. has actually been provisioned as internal
	# staff. Throwing (rather than silently stripping) surfaces the
	# conflict to the admin instead of quietly undoing their change.
	if user_doc.name == "Administrator":
		frappe.throw(_("The Administrator account cannot be used as a portal login."))

	desk_roles = set(frappe.get_all("Role", filters={"desk_access": 1}, pluck="name")) - UNIVERSAL_ROLES
	held_desk_roles = [r.role for r in user_doc.roles if r.role in desk_roles]
	if held_desk_roles:
		frappe.throw(
			_(
				"{0} already holds staff role(s) ({1}) and cannot also be used "
				"as a portal login. Use a different email address for this "
				"contact."
			).format(user_doc.name, ", ".join(held_desk_roles))
		)

	user_doc.user_type = "Website User"

	for role in portal_roles:
		if not any(r.role == role for r in user_doc.roles):
			user_doc.append("roles", {"role": role})
