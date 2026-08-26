# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
Clear discharge/gate-out/empty-return dates polluted by the Traqo BL parsing bug
where every container on a multi-container BL was parsed against the full
events_table (taking the latest dates across all containers).

Scoped to jobs still being actively synced so the scheduler or manual re-fetch
repopulates them with per-container dates using the fixed parser.
"""

import frappe

from freightmas.utils.forwarding_dnd_calculator import refresh_and_calculate_dnd

TERMINAL_STATUSES = ["Delivered", "Arrived", ""]


def execute():
	job_names = frappe.get_all(
		"Forwarding Job",
		filters={
			"enable_api_tracking": 1,
			"api_last_fetched": ["is", "set"],
			"api_tracking_status": ["not in", TERMINAL_STATUSES],
			"docstatus": ["<", 2],
		},
		pluck="name",
	)

	cleared = []

	for job_name in job_names:
		doc = frappe.get_doc("Forwarding Job", job_name)

		touched = False
		if doc.discharge_date:
			doc.discharge_date = None
			touched = True
		for row in (doc.cargo_parcel_details or []):
			if row.discharge_date or row.gate_out_date or row.empty_return_date:
				row.discharge_date = None
				row.gate_out_date = None
				row.empty_return_date = None
				touched = True

		if not touched:
			continue

		refresh_and_calculate_dnd(doc)
		doc.save(ignore_permissions=True)
		cleared.append(job_name)

	frappe.db.commit()
	frappe.logger().info(
		f"clear_bl_merged_container_tracking_dates: cleared container milestone dates "
		f"on {len(cleared)} actively-synced Forwarding Job(s): {cleared}"
	)
