import frappe
from frappe.utils import now_datetime


def update_active_tracking():
	"""Daily scheduler: update tracking data for all active Forwarding and Clearing Jobs
	with API tracking enabled.

	For Traqo, uses delta sync (updated_since) when available to limit re-fetches.
	Skips jobs where tracking status is already terminal (DELIVERED, ARRIVED)
	or where the initial fetch hasn't been done yet (api_last_fetched is NULL).
	"""
	settings = frappe.get_single("FreightMas Settings")
	if not settings.enable_shipping_tracker:
		return

	updated_refs = _get_traqo_updated_references(settings)

	_run_tracking_for_doctype("Forwarding Job", updated_refs)
	_run_tracking_for_doctype("Clearing Job", updated_refs)

	if settings.tracking_provider == "Traqo":
		frappe.db.set_single_value("FreightMas Settings", "traqo_last_sync", now_datetime())
		frappe.db.commit()


def _get_traqo_updated_references(settings):
	if settings.tracking_provider != "Traqo":
		return None

	from freightmas.integrations.tracking.dispatcher import list_updated_reference_numbers

	updated_since = settings.traqo_last_sync
	if not updated_since:
		return None

	try:
		refs = list_updated_reference_numbers(updated_since)
	except Exception:
		frappe.log_error(title="Traqo delta sync failed")
		return None

	return set(refs or [])


def _run_tracking_for_doctype(doctype, updated_refs=None):
	"""Fetch and update active tracking jobs for a given doctype."""
	terminal_statuses = ["Delivered", "Arrived", ""]

	filters = {
		"enable_api_tracking": 1,
		"api_last_fetched": ["is", "set"],
		"api_tracking_status": ["not in", terminal_statuses],
		"docstatus": ["<", 2],
	}
	if doctype == "Forwarding Job":
		filters["operational_phase"] = ["not in", ["delivered", "closed", "cancelled"]]

	jobs = frappe.get_all(
		doctype,
		filters=filters,
		fields=["name", "bl_number"],
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
	skipped = 0

	for job in jobs:
		if updated_refs is not None and job.bl_number not in updated_refs:
			skipped += 1
			continue

		try:
			fetch_containers_from_bl(job.name)
			success += 1
			frappe.db.commit()
		except Exception:
			failed += 1
			frappe.db.rollback()
			frappe.log_error(
				title=f"Tracking update failed [{doctype}]: {job.name}",
			)

	frappe.logger().info(
		f"Tracking scheduler [{doctype}]: {success} updated, {failed} failed, "
		f"{skipped} skipped (unchanged), out of {len(jobs)} jobs"
	)
