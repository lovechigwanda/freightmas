import frappe
from freightmas.utils.forwarding_dnd_calculator import refresh_and_calculate_dnd


def recalculate_open_job_dnd():
	"""Daily: recalculate DND & Storage for all open Forwarding Jobs that have DND rows populated."""
	open_jobs = frappe.get_all(
		"Forwarding Job",
		filters={
			"status": ["not in", ["Closed", "Cancelled"]],
			"docstatus": ["<", 2],
		},
		pluck="name",
	)

	success = 0
	skipped = 0
	failed = 0

	for job_name in open_jobs:
		try:
			doc = frappe.get_doc("Forwarding Job", job_name)
			if not doc.forwarding_dnd_storage_details:
				skipped += 1
				continue
			# Rebuild rows from current cargo before recalculating, so any container date
			# changes (e.g. from an API sync) are reflected in the DND figures.
			refresh_and_calculate_dnd(doc)
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			success += 1
		except Exception:
			failed += 1
			frappe.db.rollback()
			frappe.log_error(title=f"DND auto-recalc failed: {job_name}")

	frappe.logger().info(
		f"DND scheduler: {success} updated, {skipped} skipped (no DND rows), {failed} failed"
	)
