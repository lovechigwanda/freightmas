# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from freightmas.integrations.resend.client import ResendAPIError, ResendClient
from freightmas.integrations.resend.parser import parse_mime_message
from freightmas.integrations.resend.sender import resolve_sender
from freightmas.integrations.resend.settings import is_resend_enabled


def send_via_resend(email_queue, sender, recipient, message):
	"""Frappe override_email_send hook — deliver one queued email via Resend or SMTP fallback."""
	if not is_resend_enabled():
		_send_via_smtp(email_queue, sender, recipient, message)
		return

	from_address = resolve_sender(email_queue, sender)
	payload = parse_mime_message(message)
	payload["from"] = from_address
	payload["to"] = [recipient]

	if payload.get("cc"):
		payload["cc"] = [addr for addr in payload["cc"] if addr != recipient]
	if payload.get("bcc"):
		payload["bcc"] = [addr for addr in payload["bcc"] if addr != recipient]

	if not payload.get("html") and not payload.get("text"):
		payload["text"] = "(No content)"

	payload["idempotency_key"] = f"{email_queue.name}:{recipient}"

	tags = []
	if email_queue.reference_doctype:
		tags.append({"name": "doctype", "value": email_queue.reference_doctype[:50]})
	if email_queue.owner:
		tags.append({"name": "owner", "value": email_queue.owner[:50]})
	if tags:
		payload["tags"] = tags

	try:
		ResendClient().send_email(payload)
	except ResendAPIError as exc:
		frappe.log_error(
			title=f"Resend delivery failed for {email_queue.name}",
			message=(
				f"Recipient: {recipient}\n"
				f"From: {from_address}\n"
				f"Status: {exc.status_code}\n"
				f"Error: {exc}\n"
				f"Response: {exc.response_body or ''}"
			),
			reference_doctype="Email Queue",
			reference_name=email_queue.name,
		)
		raise


def _send_via_smtp(email_queue, sender, recipient, message):
	"""Fallback to the configured Email Account SMTP when Resend is disabled."""
	from frappe.email.doctype.email_queue.email_queue import SendMailContext
	from frappe.email.smtp import SMTPServer

	with SendMailContext(email_queue) as ctx:
		ctx.fetch_outgoing_server()

		if ctx.email_account_doc.service == "Frappe Mail":
			if not ctx.frappe_mail_client:
				ctx.frappe_mail_client = ctx.email_account_doc.get_frappe_mail_client()
			ctx.frappe_mail_client.send_raw(
				sender=email_queue.sender,
				recipients=recipient,
				message=message,
				is_newsletter=email_queue.reference_doctype == "Newsletter",
			)
			return

		msg_bytes = message.encode("utf-8") if isinstance(message, str) else message
		if not ctx.smtp_server:
			ctx.smtp_server = ctx.email_account_doc.get_smtp_server()

		ctx.smtp_server.session.sendmail(
			from_addr=sender or email_queue.sender,
			to_addrs=recipient,
			msg=msg_bytes,
		)
