# Keeps Client Portal accounts locked to Website User + Customer Portal
# User, and forbids a portal login from ever doubling as a staff account.
#
# Hooked from hooks.py on Contact.validate and User.validate so the
# constraint holds however the linkage is created or edited: via a Contact
# form save, a direct User edit, or "Invite as User".

import frappe
from frappe import _

from freightmas.portal.security import PORTAL_ROLE, UNIVERSAL_ROLES


def sync_portal_user_on_contact_save(doc, method=None):
	"""Contact validate hook: enforce portal constraints on doc.user."""
	if not doc.user:
		return

	is_customer_contact = any(link.link_doctype == "Customer" for link in doc.links)
	if not is_customer_contact:
		return

	user_doc = frappe.get_doc("User", doc.user)
	_apply_portal_constraints(user_doc)
	user_doc.save(ignore_permissions=True)


def enforce_portal_user_type(doc, method=None):
	"""User validate hook: re-apply portal constraints whenever the User
	record itself is edited (e.g. someone manually adds a Desk role)."""
	contact_name = frappe.db.get_value("Contact", {"user": doc.name}, "name")
	if not contact_name:
		return

	is_customer_contact = frappe.db.exists(
		"Dynamic Link",
		{"parenttype": "Contact", "parent": contact_name, "link_doctype": "Customer"},
	)
	if not is_customer_contact:
		return

	_apply_portal_constraints(doc)


def _apply_portal_constraints(user_doc):
	# user_type == "System User" is just the DocType field default for any
	# freshly created User, so it is not by itself evidence of a real staff
	# account. The meaningful signal is whether this user already holds a
	# Desk-access role — i.e. has actually been provisioned as internal
	# staff. Throwing (rather than silently stripping) surfaces the
	# conflict to the admin instead of quietly undoing their change.
	if user_doc.name == "Administrator":
		frappe.throw(_("The Administrator account cannot be used as a Client Portal login."))

	desk_roles = set(frappe.get_all("Role", filters={"desk_access": 1}, pluck="name")) - UNIVERSAL_ROLES
	held_desk_roles = [r.role for r in user_doc.roles if r.role in desk_roles]
	if held_desk_roles:
		frappe.throw(
			_(
				"{0} already holds staff role(s) ({1}) and cannot also be used "
				"as a Client Portal login. Use a different email address for "
				"this customer contact."
			).format(user_doc.name, ", ".join(held_desk_roles))
		)

	user_doc.user_type = "Website User"

	if not any(r.role == PORTAL_ROLE for r in user_doc.roles):
		user_doc.append("roles", {"role": PORTAL_ROLE})
