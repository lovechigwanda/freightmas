# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""
One-time patch: backfill the new party_type/party fields on
Client Portal Access Log from the old customer-only field, now that the
portal serves both Customer and Supplier logins.
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Client Portal Access Log"):
		return

	rows = frappe.get_all(
		"Client Portal Access Log",
		filters={"customer": ["is", "set"], "party_type": ["is", "not set"]},
		fields=["name", "customer"],
	)

	for row in rows:
		frappe.db.set_value(
			"Client Portal Access Log",
			row.name,
			{"party_type": "Customer", "party": row.customer},
			update_modified=False,
		)

	if rows:
		frappe.db.commit()

	print(f"Backfilled party_type/party on {len(rows)} Client Portal Access Log row(s).")
