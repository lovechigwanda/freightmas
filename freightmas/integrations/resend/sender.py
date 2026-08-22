# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.utils import extract_email_id, get_formatted_email, parse_addr

from freightmas.integrations.resend.settings import get_allowed_domains, get_fallback_sender

SYSTEM_USERS = frozenset({"Administrator", "Guest"})


def resolve_sender(email_queue, queue_sender: str | None = None) -> str:
	"""Pick the Resend From address for an Email Queue record."""
	queue_sender = queue_sender or email_queue.sender

	if queue_sender and _is_allowed_sender(queue_sender):
		return _normalize_sender(queue_sender)

	owner = email_queue.owner
	if owner and owner not in SYSTEM_USERS:
		owner_sender = get_formatted_email(owner)
		if owner_sender and _is_allowed_sender(owner_sender):
			return _normalize_sender(owner_sender)

	modified_by = getattr(email_queue, "modified_by", None)
	if modified_by and modified_by not in SYSTEM_USERS:
		modified_sender = get_formatted_email(modified_by)
		if modified_sender and _is_allowed_sender(modified_sender):
			return _normalize_sender(modified_sender)

	return get_fallback_sender()


def _normalize_sender(sender: str) -> str:
	sender = (sender or "").strip()
	if "<" in sender and ">" in sender:
		return sender

	name, email = parse_addr(sender)
	if name and email:
		return f"{name} <{email}>"
	return email or sender


def _is_allowed_sender(sender: str) -> bool:
	email = extract_email_id(sender).lower()
	if not email or "@" not in email:
		return False

	domain = email.rsplit("@", 1)[-1]
	return domain in get_allowed_domains()
