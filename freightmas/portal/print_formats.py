# Client portal PDF downloads via desk print formats with an explicit allowlist.

from __future__ import annotations

import frappe
from frappe import _

PORTAL_PRINT_FORMAT_DEFAULTS = {
	"Sales Invoice": "FreightMas Sales Invoice",
	"Quotation": "FreightMas Quotation",
}

SETTINGS_FIELD_BY_DOCTYPE = {
	"Sales Invoice": "portal_sales_invoice_print_format",
	"Quotation": "portal_quotation_print_format",
}


def validate_portal_print_format(
	doctype: str,
	print_format: str,
	*,
	raise_as_permission_error: bool = False,
) -> str:
	"""Ensure a print format is allowed for client portal PDF downloads."""
	if not print_format:
		frappe.throw(
			_("Print format is required for client portal downloads."),
			frappe.ValidationError,
		)

	if not frappe.db.exists("Print Format", print_format):
		frappe.throw(
			_("Print Format {0} does not exist.").format(frappe.bold(print_format)),
			frappe.ValidationError,
		)

	pf = frappe.get_cached_value(
		"Print Format",
		print_format,
		["doc_type", "disabled", "allow_client_portal_download"],
		as_dict=True,
	)

	if pf.disabled:
		frappe.throw(
			_("Print Format {0} is disabled.").format(frappe.bold(print_format)),
			frappe.ValidationError,
		)

	if pf.doc_type != doctype:
		frappe.throw(
			_("Print Format {0} is for {1}, not {2}.").format(
				frappe.bold(print_format),
				pf.doc_type,
				doctype,
			),
			frappe.ValidationError,
		)

	if not pf.get("allow_client_portal_download"):
		exc = frappe.PermissionError if raise_as_permission_error else frappe.ValidationError
		frappe.throw(
			_("Print Format {0} is not allowed for client portal downloads.").format(
				frappe.bold(print_format)
			),
			exc,
		)

	return print_format


def resolve_portal_print_format(doctype: str) -> str:
	if doctype not in SETTINGS_FIELD_BY_DOCTYPE:
		frappe.throw(_("Unsupported document type for portal PDF download: {0}").format(doctype))

	settings_field = SETTINGS_FIELD_BY_DOCTYPE[doctype]
	print_format = frappe.db.get_single_value("FreightMas Settings", settings_field)
	if not print_format:
		print_format = PORTAL_PRINT_FORMAT_DEFAULTS.get(doctype)

	return validate_portal_print_format(doctype, print_format, raise_as_permission_error=True)


def download_portal_pdf(
	*,
	doctype: str,
	name: str,
	doc,
	log_action: str,
	party_type: str,
	party: str,
):
	from freightmas.portal.security import log_portal_access

	print_format = resolve_portal_print_format(doctype)
	frappe.local.flags.ignore_print_permissions = True
	try:
		pdf_bytes = frappe.get_print(
			doctype,
			name,
			print_format=print_format,
			doc=doc,
			as_pdf=True,
		)
	finally:
		frappe.local.flags.ignore_print_permissions = False

	filename = f"{name.replace(' ', '-').replace('/', '-')}.pdf"
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "download"

	log_portal_access(
		log_action,
		doctype=doctype,
		docname=name,
		party_type=party_type,
		party=party,
	)
