# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
One-off cleanup for the future-discharge-date bug in the Searates tracking
integration (see freightmas.integrations.tracking.searates._apply_event_date):
some carriers (PIL in particular) returned forward-looking estimated "Vessel
Discharge" events, which earlier syncs recorded as if the container had
already been discharged. This clears any Forwarding Job (parent + Cargo
Parcel Details rows) whose discharge_date is still in the future, and
recalculates DND & Storage so the totals reflect the now-cleared date.
"""

import frappe
from frappe.utils import nowdate

from freightmas.utils.forwarding_dnd_calculator import refresh_and_calculate_dnd


def execute():
	today = nowdate()

	job_names = frappe.get_all(
		"Forwarding Job",
		filters={"discharge_date": [">", today]},
		pluck="name",
	)

	cleared = []

	for job_name in job_names:
		doc = frappe.get_doc("Forwarding Job", job_name)

		doc.discharge_date = None
		for row in (doc.cargo_parcel_details or []):
			if row.discharge_date and row.discharge_date > frappe.utils.getdate(today):
				row.discharge_date = None

		refresh_and_calculate_dnd(doc)
		doc.save(ignore_permissions=True)
		cleared.append(job_name)

	frappe.db.commit()
	frappe.logger().info(
		f"clear_future_discharge_dates: cleared future discharge_date on {len(cleared)} "
		f"Forwarding Job(s): {cleared}"
	)
