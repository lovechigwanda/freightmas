# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import extract_email_id

from freightmas.integrations.resend.client import ResendAPIError, ResendClient, VERIFIED_DOMAIN_STATUSES
from freightmas.integrations.resend.settings import get_fallback_sender

RESEND_TAG_MAX_LENGTH = 256
_INVALID_TAG_CHAR = re.compile(r"[^A-Za-z0-9_-]")
_MULTI_UNDERSCORE = re.compile(r"_+")


def sanitize_resend_tag(value: str | None, *, max_length: int = RESEND_TAG_MAX_LENGTH) -> str | None:
	"""Return a Resend-safe tag value or None when nothing usable remains."""
	if not value:
		return None

	clean = _INVALID_TAG_CHAR.sub("_", value.strip())
	clean = _MULTI_UNDERSCORE.sub("_", clean).strip("_")
	if not clean:
		return None

	return clean[:max_length]


def sender_domain(sender: str) -> str:
	return extract_email_id(sender).rsplit("@", 1)[-1].lower()


def resolve_test_sender(settings) -> str:
	"""Test emails always send from the configured fallback sender."""
	if settings.fallback_sender:
		return settings.fallback_sender
	return get_fallback_sender()


def validate_sender_for_resend(api_key: str, sender: str) -> dict[str, str]:
	"""Check whether the sender domain is verified for this API key's Resend account."""
	domain = sender_domain(sender)
	if not domain:
		frappe.throw(_("Could not determine the sender domain from: {0}").format(sender))

	try:
		client = ResendClient(api_key=api_key)
		domain_status = client.get_domain_status_map()
	except ResendAPIError as exc:
		# Send-only keys cannot list domains; Resend validates the From domain on send.
		if exc.is_send_only_key_restriction():
			return {}
		frappe.throw(
			_("Could not read domains from Resend ({0}): {1}").format(exc.status_code, exc),
			title=_("Resend Error"),
		)

	status = domain_status.get(domain)
	if status in VERIFIED_DOMAIN_STATUSES:
		return domain_status

	if not domain_status:
		frappe.throw(
			_(
				"No domains are linked to this API key in Resend. Add and verify <strong>{0}</strong> at "
				"<a href='https://resend.com/domains' target='_blank'>resend.com/domains</a>, using the same "
				"Resend account that owns this API key."
			).format(domain),
			title=_("Resend Domain Not Found"),
		)

	if status:
		frappe.throw(
			_(
				"<strong>{0}</strong> exists in your Resend account but its status is <strong>{1}</strong>, not verified. "
				"Complete DNS verification in the Resend dashboard, then try again."
			).format(domain, status),
			title=_("Resend Domain Not Verified"),
		)

	known = ", ".join(f"{name} ({status})" for name, status in sorted(domain_status.items())) or _("none")
	frappe.throw(
		_(
			"The test email sends <strong>from</strong> {0} (domain: <strong>{1}</strong>). "
			"That domain is not registered for this API key. Domains visible to this key: {2}. "
			"Use an API key from the same Resend account where {1} is verified, or update Fallback Sender "
			"to an address on a verified domain."
		).format(sender, domain, known),
		title=_("Resend Domain Mismatch"),
	)


def format_resend_error(exc: ResendAPIError, sender: str, recipient: str) -> str:
	domain = sender_domain(sender)
	message = str(exc)

	if "domain is not verified" in message.lower():
		return _(
			"Resend rejected the sender domain <strong>{0}</strong> for From address {1}. "
			"The recipient ({2}) does not need to be verified — only the From domain does. "
			"Confirm that {0} is verified in the same Resend account as your API key."
		).format(domain, sender, recipient)

	return _("Resend rejected the test email ({0}): {1}. From: {2}").format(
		exc.status_code, message, sender
	)
