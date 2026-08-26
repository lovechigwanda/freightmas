# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""FreightMas email layout helpers — branding, wrapping, and HTML building blocks."""

from __future__ import annotations

import re

import frappe
from frappe.utils import formatdate, get_url, today

from freightmas.utils.email_theme import EMAIL_THEME

_WRAP_MARKER = 'data-fm-email="1"'
_HTML_TAG_RE = re.compile(r"<\s*[a-zA-Z]")


def get_email_branding_context(company: str | None = None) -> dict:
	"""Return company branding fields for email templates."""
	company = company or frappe.defaults.get_global_default("company") or frappe.defaults.get_user_default("Company")
	if not company:
		return {
			"company": None,
			"company_name": "FreightMas",
			"logo": None,
			"logo_url": None,
			"logo_initial": "F",
			"phone": None,
			"email": None,
			"address": "",
		}

	info = frappe.db.get_value(
		"Company",
		company,
		["company_name", "company_logo", "phone_no", "email"],
		as_dict=True,
	) or {}

	address_line = ""
	address = frappe.get_all(
		"Address",
		filters={"link_doctype": "Company", "link_name": company},
		fields=["address_line1", "address_line2", "city", "country"],
		limit=1,
	)
	if address:
		a = address[0]
		parts = [p for p in [a.address_line1, a.address_line2, a.city, a.country] if p]
		address_line = ", ".join(parts)

	company_name = info.get("company_name") or company
	logo = info.get("company_logo")
	logo_url = None
	if logo:
		logo_url = logo if logo.startswith(("http://", "https://")) else get_url() + logo

	return {
		"company": company,
		"company_name": company_name,
		"logo": logo,
		"logo_url": logo_url,
		"logo_initial": (company_name[:1] or "F").upper(),
		"phone": info.get("phone_no"),
		"email": info.get("email"),
		"address": address_line,
	}


def format_email_date(value=None) -> str:
	"""Format a date for the email header, e.g. 14 Aug 2026."""
	value = value or today()
	return formatdate(value, "dd MMM yyyy")


def is_wrapped_email(html: str) -> bool:
	return bool(html and _WRAP_MARKER in html)


def prepare_email_body(message: str) -> str:
	"""Convert plain text to simple HTML paragraphs; preserve existing HTML."""
	if not message:
		return ""
	if _HTML_TAG_RE.search(message):
		return message

	parts = []
	for paragraph in message.split("\n\n"):
		paragraph = paragraph.strip()
		if not paragraph:
			continue
		safe = frappe.utils.escape_html(paragraph).replace("\n", "<br>")
		parts.append(
			f'<p style="margin: 0 0 {EMAIL_THEME["block_spacing"]}; '
			f'font-family: {EMAIL_THEME["font_family"]}; font-size: {EMAIL_THEME["body_size"]}; '
			f'line-height: {EMAIL_THEME["body_line_height"]}; color: {EMAIL_THEME["body_text"]};">{safe}</p>'
		)
	return "".join(parts)


def render_headline(text: str) -> str:
	safe = frappe.utils.escape_html(text)
	return (
		f'<p style="margin: 0 0 {EMAIL_THEME["block_spacing"]}; '
		f'font-family: {EMAIL_THEME["font_family"]}; font-size: {EMAIL_THEME["headline_size"]}; '
		f'font-weight: 700; line-height: 1.3; color: {EMAIL_THEME["headline_text"]};">{safe}</p>'
	)


def render_sign_off(company_name: str) -> str:
	safe = frappe.utils.escape_html(company_name or "FreightMas")
	return (
		f'<div style="margin: 32px 0 0; padding-top: 16px; border-top: 1px solid {EMAIL_THEME["card_border"]};">'
		f'<p style="margin: 0; color: {EMAIL_THEME["value_text"]};">Yours faithfully,<br>'
		f'<strong>{safe}</strong></p></div>'
	)


def render_detail_card(title: str, rows: list[tuple[str, str]], *, value_style: dict | None = None) -> str:
	"""Render a label/value detail card. rows: [(label, value), ...]."""
	value_style = value_style or {}
	value_color = value_style.get("color", EMAIL_THEME["value_text"])
	value_weight = value_style.get("font_weight", "600")

	row_html = []
	for label, value in rows:
		if value is None or value == "":
			continue
		safe_label = frappe.utils.escape_html(label)
		safe_value = frappe.utils.escape_html(str(value))
		row_html.append(
			f'<tr>'
			f'<td style="padding: 2px 12px 2px 0; width: {EMAIL_THEME["label_width"]}; '
			f'color: {EMAIL_THEME["muted_text"]}; vertical-align: top; '
			f'font-size: {EMAIL_THEME["detail_size"]};">{safe_label}</td>'
			f'<td style="padding: 2px 0; font-weight: {value_weight}; color: {value_color}; '
			f'font-size: {EMAIL_THEME["detail_size"]};">{safe_value}</td>'
			f'</tr>'
		)

	if not row_html:
		return ""

	safe_title = frappe.utils.escape_html(title)
	return (
		f'<div style="background: {EMAIL_THEME["card_bg"]}; border: 1px solid {EMAIL_THEME["card_border"]}; '
		f'border-radius: 8px; padding: 16px; margin: 0 0 {EMAIL_THEME["block_spacing"]};">'
		f'<p style="margin: 0 0 10px; font-size: {EMAIL_THEME["section_label_size"]}; font-weight: 600; '
		f'letter-spacing: 0.05em; text-transform: uppercase; color: {EMAIL_THEME["muted_text"]};">{safe_title}</p>'
		f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
		f'style="border-collapse: collapse; width: 100%;">{"".join(row_html)}</table></div>'
	)


def render_alert_box(
	title: str,
	content_html: str,
	*,
	kind: str = "warning",
) -> str:
	"""Render a warning or info callout box."""
	if kind == "info":
		bg = EMAIL_THEME["info_bg"]
		border = EMAIL_THEME["info_border"]
		title_color = EMAIL_THEME["info_title"]
		text_color = EMAIL_THEME["info_text"]
	else:
		bg = EMAIL_THEME["warning_bg"]
		border = EMAIL_THEME["warning_border"]
		title_color = EMAIL_THEME["warning_title"]
		text_color = EMAIL_THEME["warning_text"]

	safe_title = frappe.utils.escape_html(title)
	return (
		f'<div style="background: {bg}; border: 1px solid {border}; border-radius: 8px; '
		f'padding: 14px 16px; margin: 0 0 {EMAIL_THEME["block_spacing"]};">'
		f'<p style="margin: 0 0 8px; font-size: {EMAIL_THEME["detail_size"]}; font-weight: 600; '
		f'color: {title_color};">{safe_title}</p>'
		f'<div style="font-size: {EMAIL_THEME["detail_size"]}; color: {text_color};">{content_html}</div>'
		f'</div>'
	 )


def render_freightmas_email(
	body_html: str,
	*,
	company: str | None = None,
	email_type: str | None = None,
	preheader: str | None = None,
	headline: str | None = None,
	email_date: str | None = None,
	**extra_context,
) -> str:
	"""Wrap arbitrary HTML body content in the FreightMas email layout."""
	if is_wrapped_email(body_html):
		return body_html

	if headline:
		body_html = render_headline(headline) + (body_html or "")

	branding = get_email_branding_context(company)
	context = {
		**branding,
		"theme": EMAIL_THEME,
		"body": body_html or "",
		"email_type": email_type,
		"preheader": preheader,
		"email_date": email_date or format_email_date(),
		**extra_context,
	}
	return frappe.render_template("freightmas/templates/emails/freightmas_email_base.html", context)


def send_freightmas_email(
	*,
	recipients,
	subject: str,
	message: str,
	email_type: str,
	headline: str | None = None,
	company: str | None = None,
	preheader: str | None = None,
	**sendmail_kwargs,
):
	"""Prepare, wrap, and send a FreightMas-branded email."""
	body = prepare_email_body(message)
	wrapped = render_freightmas_email(
		body,
		company=company,
		email_type=email_type,
		headline=headline,
		preheader=preheader,
	)
	frappe.sendmail(recipients=recipients, subject=subject, message=wrapped, **sendmail_kwargs)
