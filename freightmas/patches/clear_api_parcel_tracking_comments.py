"""Clear parcel tracking_comment values that duplicate API-built status text."""

import frappe

from freightmas.integrations.tracking.status_labels import build_tracking_comment


def execute():
	rows = frappe.db.sql(
		"""
		SELECT parent, name, tracking_comment, api_container_status,
			api_last_event, api_last_event_date
		FROM `tabCargo Parcel Details`
		WHERE IFNULL(tracking_comment, '') != ''
		""",
		as_dict=True,
	)

	for row in rows:
		comment = (row.tracking_comment or "").strip()
		if not comment:
			continue

		api_event = (row.api_last_event or "").strip()
		status = (row.api_container_status or "").strip()
		date_str = ""
		if row.api_last_event_date:
			try:
				from frappe.utils import getdate

				date_str = getdate(row.api_last_event_date).strftime("%d-%b-%y")
			except Exception:
				date_str = str(row.api_last_event_date)

		built = build_tracking_comment(status, "", api_event, date_str, True)
		if comment == built or comment == api_event:
			frappe.db.set_value(
				"Cargo Parcel Details",
				row.name,
				"tracking_comment",
				"",
				update_modified=False,
			)

	frappe.db.commit()
