# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils.password import get_decrypted_password, rename_password_field


def execute():
	_rename_password_field()
	_repair_singles_placeholder()


def _rename_password_field():
	if not frappe.db.exists("DocType", "Resend Settings"):
		return

	if frappe.db.exists("__Auth", {"doctype": "Resend Settings", "fieldname": "api_key"}):
		rename_password_field("Resend Settings", "api_key", "resend_api_key")

	if frappe.db.exists("Singles", {"doctype": "Resend Settings", "field": "api_key"}):
		value = frappe.db.get_single_value("Resend Settings", "api_key")
		frappe.db.set_single_value("Resend Settings", "resend_api_key", value)
		frappe.db.delete("Singles", {"doctype": "Resend Settings", "field": "api_key"})


def _repair_singles_placeholder():
	"""Ensure tabSingles only stores asterisk placeholders, not stray plaintext."""
	key = get_decrypted_password(
		"Resend Settings", "Resend Settings", "resend_api_key", raise_exception=False
	)
	if not key:
		return

	current = frappe.db.get_single_value("Resend Settings", "resend_api_key")
	if not current or set(current) == {"*"}:
		return

	frappe.db.set_single_value("Resend Settings", "resend_api_key", "*" * len(key))
