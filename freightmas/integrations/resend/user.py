# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import validate_email_address

from freightmas.integrations.resend.settings import get_allowed_domains, is_resend_enabled

PORTAL_USER_TYPES = frozenset({"Website User"})


def validate_user_email_domain(doc, method=None):
	"""Ensure internal users use an allowed sender domain when Resend is enabled."""
	if not is_resend_enabled():
		return

	if doc.user_type in PORTAL_USER_TYPES:
		return

	email = (doc.email or "").strip().lower()
	if not email:
		return

	validate_email_address(email, throw=True)

	domain = email.rsplit("@", 1)[-1]
	allowed = get_allowed_domains()
	if allowed and domain not in allowed:
		frappe.msgprint(
			_(
				"User email domain <strong>{0}</strong> is not in the Resend allowed domains ({1}). "
				"Outbound email from this user will use the system fallback sender."
			).format(domain, ", ".join(allowed)),
			indicator="orange",
			title=_("Resend Sender Domain"),
		)


@frappe.whitelist()
def audit_user_emails():
	"""Return users whose email is missing or not on an allowed Resend domain."""
	frappe.only_for(("System Manager", "FreightMas Admin"))

	allowed = get_allowed_domains()
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "email", "full_name"],
		order_by="name asc",
	)

	issues = []
	for user in users:
		if user.name in ("Administrator", "Guest"):
			continue

		email = (user.email or "").strip().lower()
		if not email:
			issues.append({"user": user.name, "full_name": user.full_name, "issue": "missing_email"})
			continue

		domain = email.rsplit("@", 1)[-1]
		if allowed and domain not in allowed:
			issues.append(
				{
					"user": user.name,
					"full_name": user.full_name,
					"email": email,
					"issue": "invalid_domain",
					"domain": domain,
				}
			)

	return {
		"allowed_domains": allowed,
		"total_users": len(users),
		"issues": issues,
		"issue_count": len(issues),
	}
