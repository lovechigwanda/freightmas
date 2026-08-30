# Client Portal read/write API: Quotation list, detail, approval, PDF download.

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, getdate, nowdate, today

from freightmas.portal.print_formats import download_portal_pdf
from freightmas.portal.security import (
	assert_party_scope,
	check_portal_access,
	get_portal_customer_names,
	log_portal_access,
)
from freightmas.utils.quotation import send_client_response_email

QUOTATION_LIST_FIELDS = [
	"name",
	"transaction_date",
	"valid_till",
	"workflow_state",
	"grand_total",
	"currency",
	"customer_name",
	"customer_reference",
	"job_type",
	"job_description",
	"origin_port",
	"port_of_discharge",
	"destination_port",
	"payment_terms_template",
]

QUOTATION_SEARCH_FIELDS = [
	"name",
	"customer_reference",
	"job_description",
]

PORTAL_STATUS_PENDING = ("Sent to Customer",)
PORTAL_STATUS_APPROVED = ("Accepted",)
PORTAL_STATUS_JOB_CREATED = ("JO Created",)
PORTAL_STATUS_DECLINED = ("Rejected", "Expired")
PORTAL_VISIBLE_STATES = (
	PORTAL_STATUS_PENDING
	+ PORTAL_STATUS_APPROVED
	+ PORTAL_STATUS_JOB_CREATED
	+ PORTAL_STATUS_DECLINED
)

JOB_CARD_STATES = PORTAL_STATUS_APPROVED + PORTAL_STATUS_JOB_CREATED

CLIENT_STATUS_LABELS = {
	"Sent to Customer": "Awaiting your approval",
	"Accepted": "Approved",
	"JO Created": "Job created",
	"Rejected": "Declined",
	"Expired": "Expired",
}


def _caller_customer_filter():
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			_("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)
	return customers


def _base_quotation_filters(customers):
	return {
		"docstatus": 1,
		"quotation_to": "Customer",
		"party_name": ["in", customers],
	}


def _status_filter(status):
	status = (status or "pending").lower()
	if status == "pending":
		return list(PORTAL_STATUS_PENDING)
	if status == "approved":
		return list(PORTAL_STATUS_APPROVED)
	if status == "job_created":
		return list(PORTAL_STATUS_JOB_CREATED)
	if status == "declined":
		return list(PORTAL_STATUS_DECLINED)
	frappe.throw(_("Invalid quotation status filter."), frappe.ValidationError)


def _quotation_search_or_filters(search):
	search = (search or "").strip()
	if not search:
		return None
	like = f"%{search}%"
	return [[field, "like", like] for field in QUOTATION_SEARCH_FIELDS]


def _client_status_label(workflow_state):
	return CLIENT_STATUS_LABELS.get(workflow_state, workflow_state)


def _is_expired(valid_till, ref_date=None):
	if not valid_till:
		return False
	ref_date = ref_date or getdate(nowdate())
	return getdate(valid_till) < ref_date


def _linked_shipment_for_quotation(quotation_name):
	job_order = frappe.db.get_value(
		"Job Order",
		{"quotation_reference": quotation_name, "docstatus": ["<", 2]},
		["name", "forwarding_job_reference"],
		as_dict=True,
	)
	if not job_order or not job_order.forwarding_job_reference:
		return None, None

	job = frappe.db.get_value(
		"Forwarding Job",
		job_order.forwarding_job_reference,
		["name", "customer_reference", "cargo_count", "cargo_description"],
		as_dict=True,
	)
	if not job:
		return job_order.forwarding_job_reference, None
	return job.name, job


def _decorate_quotation_row(row, ref_date=None):
	ref_date = ref_date or getdate(nowdate())
	row["client_status"] = _client_status_label(row.get("workflow_state"))
	row["is_expired"] = _is_expired(row.get("valid_till"), ref_date)
	row["can_approve"] = (
		row.get("workflow_state") == "Sent to Customer" and not row["is_expired"]
	)
	row["can_reject"] = row["can_approve"]
	return row


def _enrich_shipment_context(rows):
	for row in rows:
		job_name, job = _linked_shipment_for_quotation(row["name"])
		row["job_name"] = job_name
		if job:
			row["job_customer_reference"] = job.customer_reference
			row["job_cargo_count"] = frappe.utils.cint(job.cargo_count) or None
			row["job_cargo_description"] = job.cargo_description
	return rows


def _serialize_quotation_row(row, ref_date=None):
	out = {field: row.get(field) for field in QUOTATION_LIST_FIELDS}
	return _decorate_quotation_row(out, ref_date)


def _assert_quotation_portal_visible(doc):
	if doc.docstatus != 1:
		frappe.throw(_("You do not have permission to view this record."), frappe.PermissionError)
	if doc.quotation_to != "Customer":
		frappe.throw(_("You do not have permission to view this record."), frappe.PermissionError)
	if doc.workflow_state not in PORTAL_VISIBLE_STATES:
		frappe.throw(_("You do not have permission to view this record."), frappe.PermissionError)


def _load_quotation_detail(quotation_name):
	doc = frappe.get_doc("Quotation", quotation_name)
	_assert_quotation_portal_visible(doc)

	today = getdate(nowdate())
	row = _serialize_quotation_row(doc.as_dict(), today)
	row["total"] = doc.total
	row["total_taxes_and_charges"] = doc.total_taxes_and_charges
	row["terms"] = doc.get("terms") or None
	row["tc_name"] = doc.get("tc_name") or None
	row = _enrich_shipment_context([row])[0]
	return row, doc


def _count_quotations(filters, or_filters=None):
	if or_filters:
		return len(frappe.get_all("Quotation", filters=filters, or_filters=or_filters, pluck="name"))
	return frappe.db.count("Quotation", filters=filters)


def _apply_portal_workflow(doc, action):
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		apply_workflow(doc, action)
	finally:
		frappe.set_user(original_user)


def _validate_pending_quotation(doc):
	if doc.workflow_state != "Sent to Customer":
		frappe.throw(_("This quotation is not awaiting your approval."))
	if doc.valid_till and getdate(doc.valid_till) < getdate(nowdate()):
		frappe.throw(_("This quotation has expired and can no longer be accepted."))


@frappe.whitelist()
def get_quotations(status=None, search=None, limit_start=0, limit_page_length=20):
	check_portal_access()
	customers = _caller_customer_filter()
	today = getdate(nowdate())

	filters = _base_quotation_filters(customers)
	filters["workflow_state"] = ["in", _status_filter(status)]
	or_filters = _quotation_search_or_filters(search)

	quotations = frappe.get_all(
		"Quotation",
		filters=filters,
		or_filters=or_filters,
		fields=QUOTATION_LIST_FIELDS,
		order_by="valid_till asc, transaction_date desc",
		limit_start=frappe.utils.cint(limit_start),
		limit_page_length=frappe.utils.cint(limit_page_length),
	)
	total_count = _count_quotations(filters, or_filters)

	quotations = [_serialize_quotation_row(row, today) for row in quotations]
	quotations = _enrich_shipment_context(quotations)

	party = customers[0] if len(customers) == 1 else None
	log_portal_access("list_quotations", doctype="Quotation", party_type="Customer", party=party)

	return {"quotations": quotations, "total_count": total_count}


@frappe.whitelist()
def get_quotations_summary():
	check_portal_access()
	customers = _caller_customer_filter()
	today = getdate(nowdate())

	pending_filters = {
		**_base_quotation_filters(customers),
		"workflow_state": ["in", list(PORTAL_STATUS_PENDING)],
	}
	pending_rows = frappe.get_all(
		"Quotation",
		filters=pending_filters,
		fields=["name", "grand_total", "valid_till"],
	)
	pending_total = sum((row.grand_total or 0) for row in pending_rows)
	expiring_soon = sum(
		1
		for row in pending_rows
		if row.valid_till and getdate(row.valid_till) <= add_days(today, 7)
	)

	approved_count = frappe.db.count(
		"Quotation",
		filters={
			**_base_quotation_filters(customers),
			"workflow_state": ["in", list(PORTAL_STATUS_APPROVED)],
		},
	)
	job_created_count = frappe.db.count(
		"Quotation",
		filters={
			**_base_quotation_filters(customers),
			"workflow_state": ["in", list(PORTAL_STATUS_JOB_CREATED)],
		},
	)
	declined_count = frappe.db.count(
		"Quotation",
		filters={
			**_base_quotation_filters(customers),
			"workflow_state": ["in", list(PORTAL_STATUS_DECLINED)],
		},
	)

	return {
		"pending_count": len(pending_rows),
		"pending_total": pending_total,
		"expiring_soon_count": expiring_soon,
		"approved_count": approved_count,
		"job_created_count": job_created_count,
		"declined_count": declined_count,
	}


@frappe.whitelist()
def get_quotation_detail(quotation_name):
	check_portal_access()
	customers = get_portal_customer_names()
	assert_party_scope("Quotation", quotation_name, "party_name", customers)

	row, _doc = _load_quotation_detail(quotation_name)

	log_portal_access(
		"view_quotation",
		doctype="Quotation",
		docname=quotation_name,
		party_type="Customer",
		party=row.get("party_name") or _doc.party_name,
	)

	return row


@frappe.whitelist()
def get_job_quotations(job_name):
	"""Return approved quotations linked to a scoped Forwarding Job."""
	check_portal_access()
	customer = assert_party_scope(
		"Forwarding Job", job_name, "customer", get_portal_customer_names()
	)

	job_order_name = frappe.db.get_value("Forwarding Job", job_name, "job_order_reference")
	if not job_order_name:
		log_portal_access(
			"view_shipment_quotations",
			doctype="Forwarding Job",
			docname=job_name,
			party_type="Customer",
			party=customer,
		)
		return {"quotations": []}

	quotation_name = frappe.db.get_value("Job Order", job_order_name, "quotation_reference")
	if not quotation_name:
		log_portal_access(
			"view_shipment_quotations",
			doctype="Forwarding Job",
			docname=job_name,
			party_type="Customer",
			party=customer,
		)
		return {"quotations": []}

	assert_party_scope("Quotation", quotation_name, "party_name", [customer])

	filters = {
		**_base_quotation_filters([customer]),
		"name": quotation_name,
		"workflow_state": ["in", list(JOB_CARD_STATES)],
	}
	rows = frappe.get_all("Quotation", filters=filters, fields=QUOTATION_LIST_FIELDS)
	today = getdate(nowdate())
	quotations = [_serialize_quotation_row(row, today) for row in rows]
	quotations = _enrich_shipment_context(quotations)
	for row in quotations:
		row["job_name"] = job_name

	log_portal_access(
		"view_shipment_quotations",
		doctype="Forwarding Job",
		docname=job_name,
		party_type="Customer",
		party=customer,
	)

	return {"quotations": quotations}


@frappe.whitelist()
def download_quotation_pdf(quotation_name):
	check_portal_access()
	customers = get_portal_customer_names()
	assert_party_scope("Quotation", quotation_name, "party_name", customers)

	doc = frappe.get_doc("Quotation", quotation_name)
	_assert_quotation_portal_visible(doc)

	download_portal_pdf(
		doctype="Quotation",
		name=quotation_name,
		doc=doc,
		log_action="download_quotation_pdf",
		party_type="Customer",
		party=doc.party_name,
	)


@frappe.whitelist(methods=["POST"])
def approve_quotation(quotation_name):
	check_portal_access()
	customers = get_portal_customer_names()
	assert_party_scope("Quotation", quotation_name, "party_name", customers)

	doc = frappe.get_doc("Quotation", quotation_name)
	_assert_quotation_portal_visible(doc)
	_validate_pending_quotation(doc)

	_apply_portal_workflow(doc, "Mark Accepted")
	doc.reload()
	send_client_response_email(doc)

	log_portal_access(
		"approve_quotation",
		doctype="Quotation",
		docname=quotation_name,
		party_type="Customer",
		party=doc.party_name,
	)

	row, _doc = _load_quotation_detail(quotation_name)
	return row


@frappe.whitelist(methods=["POST"])
def reject_quotation(quotation_name, reason=None):
	check_portal_access()
	customers = get_portal_customer_names()
	assert_party_scope("Quotation", quotation_name, "party_name", customers)

	doc = frappe.get_doc("Quotation", quotation_name)
	_assert_quotation_portal_visible(doc)
	_validate_pending_quotation(doc)

	_apply_portal_workflow(doc, "Mark Rejected")
	doc.reload()

	reason = (reason or "").strip()
	if reason:
		doc.add_comment("Comment", _("Client declined: {0}").format(reason))

	send_client_response_email(doc)

	log_portal_access(
		"reject_quotation",
		doctype="Quotation",
		docname=quotation_name,
		party_type="Customer",
		party=doc.party_name,
	)

	row, _doc = _load_quotation_detail(quotation_name)
	return row
