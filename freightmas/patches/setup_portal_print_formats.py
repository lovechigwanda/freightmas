# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""Portal print format allowlist: custom field, backfill, and settings defaults."""

import frappe

PORTAL_ALLOWED_FORMATS = (
	"FreightMas Sales Invoice",
	"FreightMas Quotation",
)

SETTINGS_DEFAULTS = {
	"portal_sales_invoice_print_format": "FreightMas Sales Invoice",
	"portal_quotation_print_format": "FreightMas Quotation",
}


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Print Format": [
				{
					"fieldname": "allow_client_portal_download",
					"label": "Allow Client Portal Download",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "disabled",
					"description": (
						"When enabled, this print format may be selected in FreightMas Settings "
						"for client portal PDF downloads."
					),
				}
			]
		},
		ignore_validate=True,
	)

	for print_format in PORTAL_ALLOWED_FORMATS:
		if frappe.db.exists("Print Format", print_format):
			frappe.db.set_value(
				"Print Format",
				print_format,
				"allow_client_portal_download",
				1,
				update_modified=False,
			)

	for fieldname, print_format in SETTINGS_DEFAULTS.items():
		if frappe.db.exists("Print Format", print_format):
			frappe.db.set_single_value(
				"FreightMas Settings",
				fieldname,
				print_format,
				update_modified=False,
			)

	frappe.clear_cache(doctype="Print Format")
