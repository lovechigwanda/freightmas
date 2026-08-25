# Client Portal document access for Forwarding Job documentation checklist rows.
#
# Outgoing documents are internal-staff uploads on the job's documents_checklist
# where client_view is enabled. Files are always private (see portal/attachments.py);
# the portal never exposes raw /private/files URLs - downloads go through the
# whitelisted endpoint below after customer-scope verification.

import os

import frappe
from frappe import _
from frappe.utils import cint

from freightmas.portal.security import assert_customer_scope, check_portal_access, log_portal_access


def _checklist_row_map(doc):
	"""Map child-row name -> row for the job's documents checklist."""
	return {row.name: row for row in (doc.get("documents_checklist") or [])}


def _file_name_from_attach(attach):
	if not attach:
		return ""
	return os.path.basename(attach)


def _serialize_outgoing_row(row):
	attach = row.attach or ""
	return {
		"name": row.name,
		"document": row.document,
		"document_label": row.document or "",
		"file_name": _file_name_from_attach(attach),
		"is_verified": bool(row.is_verified),
		"date_verified": row.date_verified,
		"date_submitted": row.date_submitted,
	}


def _get_client_visible_outgoing(doc):
	rows = []
	for row in doc.get("documents_checklist") or []:
		if not cint(row.get("client_view")):
			continue
		if not row.attach:
			continue
		rows.append(_serialize_outgoing_row(row))
	return rows


@frappe.whitelist()
def get_job_documents(job_name):
	"""Return Outgoing/Incoming document lists for a scoped Forwarding Job."""
	check_portal_access()
	customer = assert_customer_scope("Forwarding Job", job_name, "customer")

	doc = frappe.get_doc("Forwarding Job", job_name)
	outgoing = _get_client_visible_outgoing(doc)

	log_portal_access(
		"view_shipment_documents",
		doctype="Forwarding Job",
		docname=job_name,
		customer=customer,
	)

	return {
		"outgoing": outgoing,
		"incoming": [],
	}


@frappe.whitelist()
def download_job_document(job_name, checklist_row):
	"""Stream a client-visible checklist attachment after scope checks."""
	check_portal_access()
	customer = assert_customer_scope("Forwarding Job", job_name, "customer")

	doc = frappe.get_doc("Forwarding Job", job_name)
	row = _checklist_row_map(doc).get(checklist_row)
	if not row or not cint(row.get("client_view")) or not row.attach:
		frappe.throw(_("You do not have permission to download this document."), frappe.PermissionError)

	file_doc = frappe.db.get_value(
		"File",
		{"file_url": row.attach},
		["name", "file_name", "is_private"],
		as_dict=True,
	)
	if not file_doc:
		frappe.throw(_("File not found."), frappe.DoesNotExistError)

	content = frappe.get_doc("File", file_doc.name).get_content()
	frappe.local.response.filename = file_doc.file_name or _file_name_from_attach(row.attach)
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"

	log_portal_access(
		"download_shipment_document",
		doctype="Forwarding Job",
		docname=job_name,
		customer=customer,
	)
