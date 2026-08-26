# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Upsert FreightMas branded Email Template records."""

import frappe

from freightmas.notifications.email_templates import TEMPLATE_REGISTRY


def execute():
	for name, meta in TEMPLATE_REGISTRY.items():
		_upsert_template(name, meta["subject"], meta["response_html"])


def _upsert_template(name, subject, response_html):
	if frappe.db.exists("Email Template", name):
		frappe.db.set_value(
			"Email Template",
			name,
			{"subject": subject, "use_html": 1, "response_html": response_html},
			update_modified=True,
		)
		return

	doc = frappe.new_doc("Email Template")
	doc.name = name
	doc.subject = subject
	doc.use_html = 1
	doc.response_html = response_html
	doc.insert(ignore_permissions=True)
