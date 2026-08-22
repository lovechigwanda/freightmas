# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import extract_email_id


def email_domain(email: str | None) -> str | None:
	address = extract_email_id((email or "").strip()).lower()
	if not address or "@" not in address:
		return None
	return address.rsplit("@", 1)[-1]


def get_site_sending_domain() -> str | None:
	"""Best-effort sending domain derived from this site's configuration."""
	outgoing_email = frappe.db.get_value(
		"Email Account",
		{"default_outgoing": 1, "enable_outgoing": 1},
		"email_id",
	)
	if domain := email_domain(outgoing_email):
		return domain

	default_company = frappe.db.get_single_value("Global Defaults", "default_company")
	if default_company:
		company_email = frappe.db.get_value("Company", default_company, "email")
		if domain := email_domain(company_email):
			return domain

	for row in frappe.get_all("Company", filters={"email": ["is", "set"]}, fields=["email"], limit=5):
		if domain := email_domain(row.email):
			return domain

	admin_email = frappe.db.get_value("User", "Administrator", "email")
	if domain := email_domain(admin_email):
		return domain

	return None


def domain_display_name(domain: str) -> str:
	"""Turn a domain like zvomaita.co.zw into a readable sender name."""
	skip = {"mail", "smtp", "www", "noreply", "co", "com", "org", "net", "io", "zw", "za", "uk", "us"}
	for part in domain.lower().split("."):
		if part and part not in skip:
			return part.replace("-", " ").title()
	return domain.replace("-", " ").title()


def get_sender_display_name() -> str:
	"""Friendly From name for system/fallback emails on this site."""
	default_company = frappe.db.get_single_value("Global Defaults", "default_company")
	if default_company:
		company_name = frappe.db.get_value("Company", default_company, "company_name")
		if company_name:
			return company_name

	domain = get_site_sending_domain()
	if domain:
		return domain_display_name(domain)

	app_titles = frappe.get_hooks("app_title", app_name="freightmas") or []
	if app_titles:
		return app_titles[0]

	return frappe.local.site or "Support"


def get_app_sender_name() -> str:
	return get_sender_display_name()


def get_default_fallback_sender() -> str:
	domain = get_site_sending_domain()
	if not domain:
		return ""
	return f"{get_sender_display_name()} <noreply@{domain}>"


def get_default_allowed_domains_text() -> str:
	return get_site_sending_domain() or ""


def get_noreply_email() -> str | None:
	domain = get_site_sending_domain()
	return f"noreply@{domain}" if domain else None
