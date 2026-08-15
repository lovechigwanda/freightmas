# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
Set no_copy on invoice job-link and system-managed fields so duplicates
do not carry job references, register back-links, or recognition snapshots.
"""

import frappe

NO_COPY_FIELDS = {
	"Sales Invoice": [
		"forwarding_job_reference",
		"clearing_job_reference",
		"trip_reference",
		"road_freight_job_reference",
		"warehouse_job_reference",
		"border_clearing_job_reference",
		"is_forwarding_invoice",
		"is_trip_invoice",
		"is_clearing_invoice",
		"is_road_freight_invoice",
		"is_warehouse_invoice",
		"is_border_clearing_invoice",
		"invoice_register_entry",
	],
	"Purchase Invoice": [
		"forwarding_job_reference",
		"clearing_job_reference",
		"trip_reference",
		"road_freight_job_reference",
		"warehouse_job_reference",
		"border_clearing_job_reference",
		"is_forwarding_invoice",
		"is_trip_invoice",
		"is_clearing_invoice",
		"is_road_freight_invoice",
		"is_warehouse_invoice",
		"is_border_clearing_invoice",
		"invoice_register_entry",
	],
	"Sales Invoice Item": ["actual_income_account"],
	"Purchase Invoice Item": ["actual_expense_account"],
}

IRE_FIELD = {
	"fieldname": "invoice_register_entry",
	"label": "Invoice Register Entry",
	"fieldtype": "Link",
	"options": "Invoice Register Entry",
	"insert_after": "border_clearing_job_reference",
	"read_only": 1,
	"allow_on_submit": 1,
	"no_copy": 1,
}


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	# Ensure register back-link fields exist before toggling no_copy.
	create_custom_fields({
		dt: [IRE_FIELD]
		for dt in ("Sales Invoice", "Purchase Invoice")
	}, ignore_validate=True)

	for dt, fieldnames in NO_COPY_FIELDS.items():
		for fieldname in fieldnames:
			name = f"{dt}-{fieldname}"
			if not frappe.db.exists("Custom Field", name):
				continue
			frappe.db.set_value("Custom Field", name, "no_copy", 1, update_modified=False)

	frappe.clear_cache(doctype="Sales Invoice")
	frappe.clear_cache(doctype="Purchase Invoice")
