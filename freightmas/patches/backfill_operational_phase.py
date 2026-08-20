# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Backfill operational_phase and operational_substage on existing Forwarding Jobs."""

import frappe

from freightmas.forwarding_service.utils.operational_phase import derive_operational_phase


def execute():
	if not frappe.db.has_column("Forwarding Job", "operational_phase"):
		return

	jobs = frappe.get_all("Forwarding Job", pluck="name")
	for name in jobs:
		doc = frappe.get_doc("Forwarding Job", name)
		result = derive_operational_phase(doc)
		frappe.db.set_value(
			"Forwarding Job",
			name,
			{
				"operational_phase": result["phase"],
				"operational_substage": result.get("substage") or "",
			},
			update_modified=False,
		)

	frappe.db.commit()
