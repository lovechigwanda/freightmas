# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from freightmas.integrations.resend.defaults import get_default_allowed_domains_text, get_default_fallback_sender


def get_resend_settings():
	"""Return cached Resend Settings single doc."""
	return frappe.get_cached_doc("Resend Settings")


def is_resend_enabled() -> bool:
	try:
		return bool(get_resend_settings().enabled)
	except Exception:
		return False


def get_api_key() -> str | None:
	settings = get_resend_settings()
	if not settings.enabled:
		return None
	return settings.get_password("api_key")


def get_allowed_domains() -> list[str]:
	settings = get_resend_settings()
	raw = (settings.allowed_domains or get_default_allowed_domains_text() or "").strip()
	return [domain.strip().lower() for domain in raw.splitlines() if domain.strip()]


def get_fallback_sender() -> str:
	settings = get_resend_settings()
	sender = (settings.fallback_sender or get_default_fallback_sender() or "").strip()
	if not sender:
		frappe.throw(
			frappe._(
				"Configure Fallback Sender in Resend Settings, or set a company/default outgoing email address so a domain can be inferred."
			)
		)
	return sender
