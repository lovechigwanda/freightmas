# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from pathlib import Path

import frappe


def sync_service_order_print_format():
	"""Push service_order.html into the Service Order Print Format record."""
	html_path = Path(__file__).with_name("service_order.html")
	html = html_path.read_text()

	if not frappe.db.exists("Print Format", "Service Order"):
		frappe.throw("Print Format 'Service Order' was not found. Run bench migrate first.")

	frappe.db.set_value("Print Format", "Service Order", "html", html, update_modified=True)
	frappe.db.commit()
	return html_path.name
