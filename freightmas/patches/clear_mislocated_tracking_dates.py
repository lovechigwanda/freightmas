# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
One-off cleanup for a second Searates tracking bug (see
freightmas.integrations.tracking.searates._apply_event_date): discharge_date /
gate_out_date / empty_return_date were matched purely by DCSA event code, with
no check on *where* the event happened - so a transshipment-port discharge
(DISC) or an export-side "empty to shipper" gate-out (GTOT, reused by
carriers for both ends of the voyage) could be recorded as if the container
had actually reached its Port of Discharge.

These are real past dates (unlike the earlier future-date bug), so
fetch_containers_from_bl()'s "only overwrite if the new value is truthy" write
path will never self-correct them - already-affected jobs need these three
fields cleared explicitly. Scoped to jobs still being actively synced (same
filter freightmas.scheduler.tracking._run_tracking_for_doctype uses), so the
existing daily scheduler naturally repopulates them correctly on its next run
using the now-fixed, location-aware parsing logic.
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
		f"clear_mislocated_tracking_dates: cleared discharge_date/gate_out_date/"
		f"empty_return_date on {len(cleared)} actively-synced Forwarding Job(s): {cleared}"
	)
