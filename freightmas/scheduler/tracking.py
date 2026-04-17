import frappe
from frappe.utils import now_datetime


def update_active_tracking():
	"""Daily scheduler: update tracking data for all active Forwarding Jobs with API tracking enabled.

	Skips jobs where tracking status is already terminal (DELIVERED, ARRIVED)
	or where the initial fetch hasn't been done yet (api_last_fetched is NULL).
	"""
	settings = frappe.get_single("FreightMas Settings")
	if not settings.enable_shipping_tracker:
		return

	jobs = frappe.get_all(
		"Forwarding Job",
		filters={
			"enable_api_tracking": 1,
			"shipment_mode": "Sea",
			"api_last_fetched": ["is", "set"],
			"api_tracking_status": ["not in", ["DELIVERED", "ARRIVED", ""]],
			"docstatus": ["<", 2],
		},
		pluck="name",
	)

	if not jobs:
		return

	from freightmas.forwarding_service.doctype.forwarding_job.forwarding_job import (
		fetch_containers_from_bl,
	)

	success = 0
	failed = 0

	for job_name in jobs:
		try:
			fetch_containers_from_bl(job_name)
			success += 1
			frappe.db.commit()
		except Exception:
			failed += 1
			frappe.db.rollback()
			frappe.log_error(
				title=f"Tracking update failed: {job_name}",
			)

	frappe.logger().info(
		f"Tracking scheduler: {success} updated, {failed} failed out of {len(jobs)} jobs"
	)
