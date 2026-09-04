# Client Portal document access for Forwarding Job documentation checklist rows.
#
# Outgoing documents are internal-staff uploads on the job's documents_checklist
# where client_view is enabled. Incoming documents are staff-requested rows
# (client_upload) or client ad-hoc submissions (uploaded_by_client). Files are
# always private (see portal/attachments.py); the portal never exposes raw
# /private/files URLs - downloads go through the whitelisted endpoint below.

import os

import frappe
from frappe import _
from frappe.utils import cint, today
from frappe.utils.file_manager import save_file

from freightmas.portal.api.shipments import NOT_ACTIVE_STATUSES
from freightmas.portal.notifications import send_client_document_upload_email
from freightmas.portal.security import assert_customer_scope, check_portal_access, log_portal_access

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({"pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx"})


def _checklist_row_map(doc):
	"""Map child-row name -> row for the job's documents checklist."""
	return {row.name: row for row in (doc.get("documents_checklist") or [])}


def _file_name_from_attach(attach):
	if not attach:
		return ""
	return os.path.basename(attach)


def _is_incoming_row(row):
	return cint(row.get("client_upload")) or cint(row.get("uploaded_by_client"))


def _row_can_upload(row):
	if cint(row.get("is_verified")):
		return False
	return _is_incoming_row(row)


def _row_can_download(row):
	return bool(row.attach) and (cint(row.get("client_view")) or _is_incoming_row(row))


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


def _serialize_incoming_row(row):
	attach = row.attach or ""
	return {
		"name": row.name,
		"document_label": row.document or "",
		"file_name": _file_name_from_attach(attach),
		"is_submitted": bool(row.is_submitted),
		"date_submitted": row.date_submitted,
		"is_verified": bool(row.is_verified),
		"can_upload": _row_can_upload(row),
		"can_download": bool(attach),
		"is_requested": bool(cint(row.get("client_upload"))),
		"is_ad_hoc": bool(cint(row.get("uploaded_by_client"))),
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


def _get_client_visible_incoming(doc):
	rows = []
	for row in doc.get("documents_checklist") or []:
		if not _is_incoming_row(row):
			continue
		rows.append(_serialize_incoming_row(row))
	return rows


def _validate_job_uploadable(job_name):
	job = frappe.db.get_value(
		"Forwarding Job",
		job_name,
		["name", "docstatus", "status", "owner"],
		as_dict=True,
	)
	if not job:
		frappe.throw(_("Shipment not found."), frappe.DoesNotExistError)
	if cint(job.docstatus) >= 2:
		frappe.throw(_("This shipment is cancelled and no longer accepts uploads."))
	if job.status in NOT_ACTIVE_STATUSES:
		frappe.throw(_("This shipment is closed and no longer accepts uploads."))
	return job


def _sanitize_filename(file_name):
	name = os.path.basename(file_name or "").strip()
	if not name:
		frappe.throw(_("File name is required."))
	if ".." in name or "/" in name or "\\" in name:
		frappe.throw(_("Invalid file name."))
	return name


def _extension_from_filename(file_name):
	base = file_name.lower()
	if base.count(".") > 1:
		frappe.throw(_("Invalid file name."))
	if "." not in base:
		frappe.throw(_("File type not allowed. Use: {0}").format(", ".join(sorted(ALLOWED_EXTENSIONS))))
	ext = base.rsplit(".", 1)[-1]
	if ext not in ALLOWED_EXTENSIONS:
		frappe.throw(_("File type not allowed. Use: {0}").format(", ".join(sorted(ALLOWED_EXTENSIONS))))
	return ext


def _read_upload_file():
	upload = frappe.request.files.get("file") if frappe.request else None
	if not upload or not getattr(upload, "filename", None):
		frappe.throw(_("No file was uploaded."))

	file_name = _sanitize_filename(upload.filename)
	_extension_from_filename(file_name)

	content = upload.stream.read()
	if not content:
		frappe.throw(_("The uploaded file is empty."))
	if len(content) > MAX_UPLOAD_SIZE_BYTES:
		frappe.throw(_("File is too large. Maximum size is 10 MB."))

	return file_name, content


def _apply_portal_job_save(job, mutate_fn):
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		mutate_fn(job)
		job.save(ignore_permissions=True)
	finally:
		frappe.set_user(original_user)


def _delete_file_for_attach(attach):
	if not attach:
		return
	file_name = frappe.db.get_value("File", {"file_url": attach}, "name")
	if file_name:
		frappe.delete_doc("File", file_name, ignore_permissions=True)


def _save_checklist_attachment(job_name, file_name, content):
	file_doc = save_file(
		file_name,
		content,
		"Forwarding Job",
		job_name,
		is_private=1,
		df="documents_checklist",
	)
	return file_doc.file_url


def _apply_submission_fields(row):
	row.is_submitted = 1
	row.date_submitted = today()
	row.is_verified = 0
	row.date_verified = None


def _find_ad_hoc_row(doc, document):
	for row in doc.get("documents_checklist") or []:
		if row.document == document and cint(row.get("uploaded_by_client")):
			return row
	return None


def _validate_upload_target_row(row, job_name):
	if not row:
		frappe.throw(_("Document row not found."), frappe.DoesNotExistError)
	if not _is_incoming_row(row):
		frappe.throw(_("You do not have permission to upload to this document."), frappe.PermissionError)
	if cint(row.get("is_verified")):
		frappe.throw(_("This document has been verified and cannot be changed."))


def _validate_clearing_document(document):
	if not document:
		frappe.throw(_("Document type is required."))
	if not frappe.db.exists("Clearing Document", document):
		frappe.throw(_("Invalid document type."), frappe.ValidationError)


def _upload_to_row(job, row, file_name, content, *, is_replace):
	old_attach = row.attach
	row_name = row.name

	def mutate(doc):
		target = _checklist_row_map(doc).get(row_name)
		if not target:
			frappe.throw(_("Document row not found."), frappe.DoesNotExistError)
		file_url = _save_checklist_attachment(doc.name, file_name, content)
		target.attach = file_url
		_apply_submission_fields(target)

	_apply_portal_job_save(job, mutate)

	if is_replace and old_attach:
		_delete_file_for_attach(old_attach)

	job.reload()
	return _checklist_row_map(job).get(row_name)


@frappe.whitelist()
def get_job_documents(job_name):
	"""Return Outgoing/Incoming document lists for a scoped Forwarding Job."""
	check_portal_access()
	customer = assert_customer_scope("Forwarding Job", job_name, "customer")

	doc = frappe.get_doc("Forwarding Job", job_name)
	outgoing = _get_client_visible_outgoing(doc)
	incoming = _get_client_visible_incoming(doc)

	log_portal_access(
		"view_shipment_documents",
		doctype="Forwarding Job",
		docname=job_name,
		customer=customer,
	)

	return {
		"outgoing": outgoing,
		"incoming": incoming,
	}


@frappe.whitelist()
def get_upload_document_types():
	"""Return Clearing Document names available for ad-hoc client uploads."""
	check_portal_access()
	return frappe.get_all("Clearing Document", pluck="name", order_by="name asc")


@frappe.whitelist(methods=["POST"])
def upload_job_document():
	"""Upload a client document to a checklist row or as a new ad-hoc submission."""
	check_portal_access()

	job_name = (frappe.form_dict.get("job_name") or "").strip()
	checklist_row = (frappe.form_dict.get("checklist_row") or "").strip()
	document = (frappe.form_dict.get("document") or "").strip()

	if not job_name:
		frappe.throw(_("Shipment is required."))
	if checklist_row and document:
		frappe.throw(_("Provide either a checklist row or a document type, not both."))
	if not checklist_row and not document:
		frappe.throw(_("Provide a checklist row or a document type."))

	customer = assert_customer_scope("Forwarding Job", job_name, "customer")
	_validate_job_uploadable(job_name)

	file_name, content = _read_upload_file()
	job = frappe.get_doc("Forwarding Job", job_name)
	is_replace = False

	if checklist_row:
		row = _checklist_row_map(job).get(checklist_row)
		_validate_upload_target_row(row, job_name)
		is_replace = bool(row.attach)
		row = _upload_to_row(job, row, file_name, content, is_replace=is_replace)
	else:
		_validate_clearing_document(document)
		existing = _find_ad_hoc_row(job, document)
		if existing:
			if cint(existing.get("is_verified")):
				frappe.throw(
					_("{0} has already been submitted and verified.").format(document),
					frappe.ValidationError,
				)
			is_replace = bool(existing.attach)
			row = _upload_to_row(job, existing, file_name, content, is_replace=is_replace)
		else:
			file_url = _save_checklist_attachment(job.name, file_name, content)

			def mutate(doc):
				new_row = doc.append(
					"documents_checklist",
					{
						"document": document,
						"attach": file_url,
						"uploaded_by_client": 1,
						"client_view": 0,
						"client_upload": 0,
					},
				)
				_apply_submission_fields(new_row)

			_apply_portal_job_save(job, mutate)
			job.reload()
			row = _find_ad_hoc_row(job, document)

	job.reload()
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		job.add_comment(
			"Comment",
			_("Client uploaded: {0} ({1})").format(row.document, file_name),
		)
	finally:
		frappe.set_user(original_user)

	send_client_document_upload_email(job, row.document, file_name)

	action = "replace_shipment_document" if is_replace else "upload_shipment_document"
	log_portal_access(
		action,
		doctype="Forwarding Job",
		docname=job_name,
		customer=customer,
	)

	return _serialize_incoming_row(row)


@frappe.whitelist()
def download_job_document(job_name, checklist_row):
	"""Stream a checklist attachment after scope checks."""
	check_portal_access()
	customer = assert_customer_scope("Forwarding Job", job_name, "customer")

	doc = frappe.get_doc("Forwarding Job", job_name)
	row = _checklist_row_map(doc).get(checklist_row)
	if not row or not row.attach or not _row_can_download(row):
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
