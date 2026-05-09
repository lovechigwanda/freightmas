import frappe
from frappe.utils import now_datetime


def update_active_tracking():
	"""Daily scheduler: update tracking data for all active Forwarding and Clearing Jobs
	with API tracking enabled.

	Skips jobs where tracking status is already terminal (DELIVERED, ARRIVED)
	or where the initial fetch hasn't been done yet (api_last_fetched is NULL).
	"""
	settings = frappe.get_single("FreightMas Settings")
	if not settings.enable_shipping_tracker:
		return

	_run_tracking_for_doctype("Forwarding Job")
	_run_tracking_for_doctype("Clearing Job")


def _run_tracking_for_doctype(doctype):
	"""Fetch and update active tracking jobs for a given doctype."""
	terminal_statuses = ["Delivered", "Arrived", ""]

	jobs = frappe.get_all(
		doctype,
		filters={
			"enable_api_tracking": 1,
			"api_last_fetched": ["is", "set"],
			"api_tracking_status": ["not in", terminal_statuses],
			"docstatus": ["<", 2],
		},
		pluck="name",
	)

	if not jobs:
		return

	if doctype == "Forwarding Job":
		from freightmas.forwarding_service.doctype.forwarding_job.forwarding_job import (
			fetch_containers_from_bl,
		)
	else:
		from freightmas.clearing_service.doctype.clearing_job.clearing_job import (
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
				title=f"Tracking update failed [{doctype}]: {job_name}",
			)

	frappe.logger().info(
		f"Tracking scheduler [{doctype}]: {success} updated, {failed} failed out of {len(jobs)} jobs"
	)
