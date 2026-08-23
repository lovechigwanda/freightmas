# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Smoke tests for the Resend email integration."""

from __future__ import annotations

import frappe

from freightmas.integrations.resend.defaults import get_noreply_email, get_site_sending_domain
from freightmas.integrations.resend.parser import parse_mime_message
from freightmas.integrations.resend.sender import resolve_sender
from freightmas.integrations.resend.settings import get_allowed_domains, is_resend_enabled
from freightmas.integrations.resend.validation import sanitize_resend_tag


def _test_tag_sanitization() -> dict:
	long_value = "a" * 300
	return {
		"doctype_spaces": sanitize_resend_tag("Forwarding Job") == "Forwarding_Job",
		"owner_email": sanitize_resend_tag("user@company.co.zw") == "user_company_co_zw",
		"empty_skipped": sanitize_resend_tag("") is None,
		"invalid_skipped": sanitize_resend_tag("!!!") is None,
		"truncated_256": len(sanitize_resend_tag(long_value) or "") == 256,
	}


def run():
	results = {
		"hook_registered": bool(frappe.get_hooks("override_email_send")),
		"resend_settings_exists": frappe.db.exists("Resend Settings", "Resend Settings"),
		"resend_enabled": is_resend_enabled(),
		"allowed_domains": get_allowed_domains(),
		"default_email_account": frappe.db.get_value(
			"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "name"
		),
		"suggested_domain": get_site_sending_domain(),
		"parser_ok": False,
		"sender_resolution_ok": False,
		"tag_sanitization": _test_tag_sanitization(),
		"user_audit": None,
	}

	noreply = get_noreply_email() or "noreply@example.com"

	sample_message = (
		f"From: Test <{noreply}>\r\n"
		"To: customer@example.com\r\n"
		"Subject: Test\r\n"
		"MIME-Version: 1.0\r\n"
		"Content-Type: text/html; charset=utf-8\r\n"
		"\r\n"
		"<p>Hello</p>"
	)
	parsed = parse_mime_message(sample_message)
	results["parser_ok"] = parsed.get("subject") == "Test" and "Hello" in parsed.get("html", "")

	attachment_message = (
		f"From: Test <{noreply}>\r\n"
		"To: customer@example.com\r\n"
		"Subject: Attachment Test\r\n"
		"MIME-Version: 1.0\r\n"
		"Content-Type: multipart/mixed; boundary=boundary\r\n"
		"\r\n"
		"--boundary\r\n"
		"Content-Type: text/html; charset=utf-8\r\n"
		"\r\n"
		"<p>Report attached</p>\r\n"
		"--boundary\r\n"
		"Content-Type: application/octet-stream\r\n"
		"Content-Disposition: attachment; filename=\"report.xlsx\"\r\n"
		"Content-Transfer-Encoding: base64\r\n"
		"\r\n"
		"UEsDBA==\r\n"
		"--boundary--\r\n"
	)
	attachment_parsed = parse_mime_message(attachment_message)
	results["attachment_parser_ok"] = (
		attachment_parsed.get("subject") == "Attachment Test"
		and len(attachment_parsed.get("attachments") or []) == 1
	)

	if results["resend_settings_exists"]:
		settings = frappe.get_single("Resend Settings")
		queue = frappe._dict(
			{
				"name": "TEST-QUEUE",
				"sender": settings.fallback_sender,
				"owner": frappe.session.user,
				"modified_by": frappe.session.user,
				"reference_doctype": None,
			}
		)
		sender = resolve_sender(queue, settings.fallback_sender)
		results["sender_resolution_ok"] = bool(sender)

	from freightmas.integrations.resend.user import audit_user_emails

	results["user_audit"] = audit_user_emails()

	print(frappe.as_json(results, indent=2))
	return results
