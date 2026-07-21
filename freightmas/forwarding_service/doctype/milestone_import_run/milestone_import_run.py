# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from freightmas.utils.permissions import check_freightmas_role
from freightmas.forwarding_service import milestone_import as mi


class MilestoneImportRun(Document):
	def validate(self):
		if not self.is_new():
			prev_status = frappe.db.get_value(self.doctype, self.name, "status")
			if prev_status == "Completed":
				frappe.throw(_("This import run is completed and locked."))

	@frappe.whitelist()
	def get_preview(self):
		check_freightmas_role()
		if not self.service_module:
			frappe.throw(_("Select a Service Module first."))
		if not self.import_file:
			frappe.throw(_("Attach a tracker file first."))

		headers, rows = mi._read_workbook(self.import_file)
		job_reference_header, column_map, _header_by_code = mi._resolve_column_map(self.service_module)
		preview = mi.classify_rows(headers, rows, job_reference_header, column_map)

		self.status = "Previewed"
		self.save()
		return preview

	@frappe.whitelist()
	def apply_import(self, updates):
		check_freightmas_role()
		if isinstance(updates, str):
			updates = frappe.parse_json(updates)

		summary = mi.apply_updates(updates)

		self.set("import_results", [])
		for row in summary["results"]:
			self.append("import_results", row)

		self.updated_count = summary["updated_count"]
		self.skipped_count = summary["skipped_count"]
		self.failed_count = summary["failed_count"]

		if summary["failed_count"] and summary["updated_count"]:
			self.status = "Partially Completed"
		elif summary["failed_count"] and not summary["updated_count"]:
			self.status = "Failed"
		else:
			self.status = "Completed"

		self.save()
		return {
			"updated_count": self.updated_count,
			"skipped_count": self.skipped_count,
			"failed_count": self.failed_count,
			"status": self.status,
		}
