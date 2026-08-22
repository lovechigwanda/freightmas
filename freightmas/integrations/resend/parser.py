# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import base64
from email import policy
from email.message import Message
from email.parser import BytesParser
from typing import Any

from frappe.utils import cstr, extract_email_id


def parse_mime_message(raw_message: str | bytes) -> dict[str, Any]:
	"""Convert a queued RFC822 message into a Resend API payload (without from)."""
	if isinstance(raw_message, str):
		raw_bytes = raw_message.encode("utf-8", errors="replace")
	else:
		raw_bytes = raw_message

	message = BytesParser(policy=policy.default).parsebytes(raw_bytes)

	payload: dict[str, Any] = {
		"subject": _decode_header(message.get("Subject")) or "(No Subject)",
		"html": "",
		"text": "",
		"cc": _parse_addresses(message.get("Cc")),
		"bcc": _parse_addresses(message.get("Bcc")),
		"reply_to": _parse_addresses(message.get("Reply-To")),
		"attachments": [],
	}

	html, text = _extract_body(message)
	payload["html"] = html
	payload["text"] = text or _plain_from_html(html)
	payload["attachments"] = _extract_attachments(message)
	return payload


def _decode_header(value) -> str:
	if value is None:
		return ""
	return cstr(value)


def _parse_addresses(value) -> list[str]:
	if not value:
		return []

	from email.utils import getaddresses

	addresses = []
	for _name, email in getaddresses([cstr(value)]):
		email = extract_email_id(email)
		if email:
			addresses.append(email)
	return addresses


def _extract_body(message: Message) -> tuple[str, str]:
	html = ""
	text = ""

	if message.is_multipart():
		for part in message.walk():
			if part.get_content_disposition() == "attachment":
				continue

			content_type = part.get_content_type()
			if content_type == "text/html" and not html:
				html = _get_part_content(part)
			elif content_type == "text/plain" and not text:
				text = _get_part_content(part)
	else:
		content_type = message.get_content_type()
		content = _get_part_content(message)
		if content_type == "text/html":
			html = content
		else:
			text = content

	return html, text


def _get_part_content(part: Message) -> str:
	try:
		content = part.get_content()
	except Exception:
		payload = part.get_payload(decode=True)
		if payload is None:
			return ""
		content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
	return cstr(content)


def _extract_attachments(message: Message) -> list[dict[str, str]]:
	attachments: list[dict[str, str]] = []

	if not message.is_multipart():
		return attachments

	for part in message.walk():
		disposition = part.get_content_disposition()
		if disposition not in ("attachment", "inline"):
			continue

		filename = part.get_filename()
		payload = part.get_payload(decode=True)
		if not filename or not payload:
			continue

		attachments.append(
			{
				"filename": filename,
				"content": base64.b64encode(payload).decode("ascii"),
			}
		)

	return attachments


def _plain_from_html(html: str) -> str:
	if not html:
		return ""
	try:
		from frappe.utils import html_to_text

		return html_to_text(html)
	except Exception:
		return ""
