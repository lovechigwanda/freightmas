# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe

from freightmas.integrations.resend.defaults import (
	get_default_allowed_domains_text,
	get_default_fallback_sender,
	get_noreply_email,
)


def execute():
	_ensure_resend_settings()
	_ensure_outgoing_email_account()


def _ensure_resend_settings():
	if frappe.db.exists("Resend Settings", "Resend Settings"):
		return

	doc = frappe.new_doc("Resend Settings")
	doc.enabled = 0
	doc.fallback_sender = get_default_fallback_sender()
	doc.allowed_domains = get_default_allowed_domains_text()
	doc.insert(ignore_permissions=True)


def _ensure_outgoing_email_account():
	email_id = get_noreply_email()
	if not email_id:
		return

	account_name = "Resend Outgoing"

	if frappe.db.exists("Email Account", account_name):
		doc = frappe.get_doc("Email Account", account_name)
	else:
		doc = frappe.new_doc("Email Account")
		doc.email_account_name = account_name

	doc.email_id = email_id
	doc.service = ""
	doc.smtp_server = "smtp.resend.com"
	doc.smtp_port = 465
	doc.use_ssl = 1
	doc.use_tls = 0
	doc.login_id_is_different = 1
	doc.login_id = "resend"
	doc.enable_outgoing = 1
	doc.default_outgoing = 1
	doc.enable_incoming = 0
	doc.always_use_account_email_id_as_sender = 0
	doc.always_use_account_name_as_sender_name = 0

	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)

	_set_default_outgoing(account_name)


def _set_default_outgoing(account_name):
	frappe.db.sql(
		"""
		UPDATE `tabEmail Account`
		SET default_outgoing = 0
		WHERE name != %s AND default_outgoing = 1
		""",
		account_name,
	)
	frappe.db.set_value("Email Account", account_name, "default_outgoing", 1)
