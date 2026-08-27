# Client Portal read API: Sales Invoice list + detail + PDF download
# ("Invoices & Billing"). Mirrors freightmas.portal.supplier.invoices
# (Purchase Invoice) almost 1:1, swapped to Customer scope - see that
# module's header comment for why no child-row scoping is needed here.

import frappe
from frappe import _
from frappe.utils import add_days, get_year_start, getdate, nowdate

from freightmas.portal.security import assert_customer_scope, check_portal_access, get_portal_customer_names, log_portal_access
from freightmas.utils.company_branding import portal_invoice_pdf_logo_injection
from freightmas.utils.statement_job_linked_export import (
	build_statement_job_linked_excel,
	build_statement_job_linked_pdf,
)

INVOICE_LIST_FIELDS = [
	"name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status",
	"is_return", "is_forwarding_invoice", "forwarding_job_reference",
	"is_clearing_invoice", "clearing_job_reference",
	"is_border_clearing_invoice", "border_clearing_job_reference",
	"is_road_freight_invoice", "road_freight_job_reference",
	"is_warehouse_invoice", "warehouse_job_reference",
	"is_trip_invoice", "trip_reference",
]

# (is_flag_fieldname, job_reference_fieldname, job doctype label) - used to
# resolve which single job reference is meaningful for display on a row,
# without the frontend needing to check all six fields itself.
JOB_REFERENCE_FLAGS = [
	("is_forwarding_invoice", "forwarding_job_reference", "Forwarding Job"),
	("is_clearing_invoice", "clearing_job_reference", "Clearing Job"),
	("is_border_clearing_invoice", "border_clearing_job_reference", "Border Clearing Job"),
	("is_road_freight_invoice", "road_freight_job_reference", "Road Freight Job"),
	("is_warehouse_invoice", "warehouse_job_reference", "Warehouse Job"),
	("is_trip_invoice", "trip_reference", "Trip"),
]

INVOICE_SEARCH_FIELDS = [
	"forwarding_job_reference",
	"clearing_job_reference",
	"border_clearing_job_reference",
	"road_freight_job_reference",
	"warehouse_job_reference",
	"trip_reference",
]

AGING_BUCKETS = ("current", "1_30", "31_60", "61_90", "over_90")


def _with_job_reference(row):
	job_doctype, job_name = None, None
	for flag, ref_field, label in JOB_REFERENCE_FLAGS:
		if row.get(flag) and row.get(ref_field):
			job_doctype, job_name = label, row.get(ref_field)
			break
	row["job_doctype"] = job_doctype
	row["job_name"] = job_name
	return row


def _enrich_job_context(rows):
	fwd_jobs = {
		row["job_name"]
		for row in rows
		if row.get("job_doctype") == "Forwarding Job" and row.get("job_name")
	}
	if not fwd_jobs:
		return rows

	job_meta = {
		job.name: job
		for job in frappe.get_all(
			"Forwarding Job",
			filters={"name": ["in", list(fwd_jobs)]},
			fields=["name", "customer_reference", "cargo_count", "cargo_description"],
		)
	}
	for row in rows:
		job = job_meta.get(row.get("job_name"))
		if job:
			row["job_customer_reference"] = job.customer_reference
			row["job_cargo_count"] = frappe.utils.cint(job.cargo_count) or None
			row["job_cargo_description"] = job.cargo_description
	return rows


def _decorate_invoice_row(row, today):
	outstanding = row.get("outstanding_amount") or 0
	due_date = row.get("due_date")
	row["is_overdue"] = bool(outstanding > 0 and due_date and getdate(due_date) < today)
	row["balance_due"] = outstanding
	return row


def _caller_customer_filter():
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			_("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)
	return customers


def _job_invoice_filters(job_name, customer):
	return {
		"docstatus": ["<", 2],
		"customer": customer,
		"is_forwarding_invoice": 1,
		"forwarding_job_reference": job_name,
	}


def _aging_bucket_filters(bucket, today):
	if bucket == "current":
		return {"due_date": [">=", today]}
	if bucket == "1_30":
		return {"due_date": ["between", [add_days(today, -30), add_days(today, -1)]]}
	if bucket == "31_60":
		return {"due_date": ["between", [add_days(today, -60), add_days(today, -31)]]}
	if bucket == "61_90":
		return {"due_date": ["between", [add_days(today, -90), add_days(today, -61)]]}
	if bucket == "over_90":
		return {"due_date": ["<", add_days(today, -90)]}
	return {}


def _build_invoice_list_filters(customers, status=None, from_date=None, to_date=None, aging_bucket=None):
	filters = {"docstatus": ["<", 2], "customer": ["in", customers]}

	if status == "Outstanding":
		filters["docstatus"] = 1
		filters["outstanding_amount"] = [">", 0]
	elif status == "Overdue":
		filters["docstatus"] = 1
		filters["outstanding_amount"] = [">", 0]
		filters["due_date"] = ["<", getdate(nowdate())]
	elif status == "Paid":
		filters["status"] = "Paid"
	elif status:
		filters["status"] = status

	if from_date:
		filters["posting_date"] = [">=", getdate(from_date)]
	if to_date:
		posting_filter = filters.get("posting_date")
		if posting_filter:
			filters["posting_date"] = ["between", [posting_filter[1], getdate(to_date)]]
		else:
			filters["posting_date"] = ["<=", getdate(to_date)]

	if aging_bucket:
		if aging_bucket not in AGING_BUCKETS:
			frappe.throw(_("Invalid aging bucket."), frappe.ValidationError)
		filters["docstatus"] = 1
		filters["outstanding_amount"] = [">", 0]
		filters.update(_aging_bucket_filters(aging_bucket, getdate(nowdate())))

	return filters


def _invoice_search_or_filters(search):
	search = (search or "").strip()
	if not search:
		return None
	like = f"%{search}%"
	or_filters = [["name", "like", like]]
	for field in INVOICE_SEARCH_FIELDS:
		or_filters.append([field, "like", like])
	return or_filters


def _compute_aging(customers, today):
	base = {"docstatus": 1, "customer": ["in", customers], "outstanding_amount": [">", 0]}
	aging = {}

	aging["current"] = _sum_and_count({**base, "due_date": [">=", today]})
	aging["1_30"] = _sum_and_count(
		{**base, "due_date": ["between", [add_days(today, -30), add_days(today, -1)]]}
	)
	aging["31_60"] = _sum_and_count(
		{**base, "due_date": ["between", [add_days(today, -60), add_days(today, -31)]]}
	)
	aging["61_90"] = _sum_and_count(
		{**base, "due_date": ["between", [add_days(today, -90), add_days(today, -61)]]}
	)
	aging["over_90"] = _sum_and_count({**base, "due_date": ["<", add_days(today, -90)]})

	return aging


def _sum_and_count(filters):
	rows = frappe.get_all(
		"Sales Invoice",
		filters=filters,
		fields=["outstanding_amount"],
	)
	amount = sum((row.outstanding_amount or 0) for row in rows)
	return {"amount": amount, "count": len(rows)}


def _default_statement_party(customers, party=None):
	if party:
		if party not in customers:
			frappe.throw(_("You do not have access to this customer account."), frappe.PermissionError)
		return party
	if len(customers) == 1:
		return customers[0]
	return customers[0]


def _statement_filters(customers, party=None, from_date=None, to_date=None):
	today = getdate(nowdate())
	party = _default_statement_party(customers, party)
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		frappe.throw(_("Company is not configured."), frappe.ValidationError)

	return {
		"party_type": "Customer",
		"party": party,
		"company": company,
		"from_date": getdate(from_date) if from_date else get_year_start(today),
		"to_date": getdate(to_date) if to_date else today,
		"include_draft_invoices": 0,
		"include_cancelled": 0,
	}


def _count_invoices(filters, or_filters=None):
	if or_filters:
		return len(frappe.get_all("Sales Invoice", filters=filters, or_filters=or_filters, pluck="name"))
	return frappe.db.count("Sales Invoice", filters=filters)


@frappe.whitelist()
def get_job_invoices(job_name):
	"""Return Sales Invoices linked to a scoped Forwarding Job."""
	check_portal_access()
	customer = assert_customer_scope("Forwarding Job", job_name, "customer")

	invoices = frappe.get_all(
		"Sales Invoice",
		filters=_job_invoice_filters(job_name, customer),
		fields=INVOICE_LIST_FIELDS,
		order_by="posting_date desc",
	)
	invoices = [_with_job_reference(row) for row in invoices]
	invoices = _enrich_job_context(invoices)

	log_portal_access(
		"view_shipment_invoices",
		doctype="Forwarding Job",
		docname=job_name,
		party_type="Customer",
		party=customer,
	)

	return {"invoices": invoices}


@frappe.whitelist()
def get_invoices(
	status=None,
	search=None,
	from_date=None,
	to_date=None,
	aging_bucket=None,
	sort_by="due_date",
	sort_order="asc",
	limit_start=0,
	limit_page_length=20,
):
	check_portal_access()
	customers = _caller_customer_filter()
	today = getdate(nowdate())

	filters = _build_invoice_list_filters(customers, status, from_date, to_date, aging_bucket)
	or_filters = _invoice_search_or_filters(search)

	sort_field = sort_by if sort_by in {"due_date", "posting_date", "outstanding_amount", "name"} else "due_date"
	sort_dir = "desc" if str(sort_order).lower() == "desc" else "asc"
	order_by = f"{sort_field} {sort_dir}, posting_date desc"

	invoices = frappe.get_all(
		"Sales Invoice",
		filters=filters,
		or_filters=or_filters,
		fields=INVOICE_LIST_FIELDS + ["docstatus"],
		order_by=order_by,
		limit_start=frappe.utils.cint(limit_start),
		limit_page_length=frappe.utils.cint(limit_page_length),
	)
	total_count = _count_invoices(filters, or_filters)

	invoices = [_decorate_invoice_row(_with_job_reference(row), today) for row in invoices]
	invoices = _enrich_job_context(invoices)

	party = customers[0] if len(customers) == 1 else None
	log_portal_access("list_invoices", doctype="Sales Invoice", party_type="Customer", party=party)

	return {"invoices": invoices, "total_count": total_count}


@frappe.whitelist()
def get_invoices_summary():
	"""Account header + aging strip for the Invoices workspace."""
	check_portal_access()
	customers = _caller_customer_filter()
	today = getdate(nowdate())

	base_filters = {"docstatus": 1, "customer": ["in", customers]}

	outstanding_amount = (
		frappe.get_all(
			"Sales Invoice",
			filters={**base_filters, "outstanding_amount": [">", 0]},
			fields=[{"SUM": "outstanding_amount", "as": "total"}],
		)[0].total
		or 0
	)
	overdue_amount = (
		frappe.get_all(
			"Sales Invoice",
			filters={**base_filters, "outstanding_amount": [">", 0], "due_date": ["<", today]},
			fields=[{"SUM": "outstanding_amount", "as": "total"}],
		)[0].total
		or 0
	)
	open_invoice_count = frappe.db.count(
		"Sales Invoice",
		filters={**base_filters, "outstanding_amount": [">", 0]},
	)
	paid_ytd = (
		frappe.db.sql(
			"""
			SELECT SUM(per.allocated_amount) AS total
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			INNER JOIN `tabSales Invoice` si ON si.name = per.reference_name
			WHERE per.reference_doctype = 'Sales Invoice'
				AND si.customer IN %(customers)s
				AND pe.docstatus = 1
				AND pe.posting_date >= %(year_start)s
			""",
			{"customers": customers, "year_start": get_year_start(today)},
			as_dict=True,
		)[0].total
		or 0
	)

	return {
		"outstanding_amount": outstanding_amount,
		"overdue_amount": overdue_amount,
		"open_invoice_count": open_invoice_count,
		"paid_ytd": paid_ytd,
		"aging": _compute_aging(customers, today),
		"statement_party": customers[0] if len(customers) == 1 else None,
		"customers": customers,
	}


@frappe.whitelist()
def get_invoice_detail(invoice_name):
	check_portal_access()
	customer = assert_customer_scope("Sales Invoice", invoice_name)

	row = frappe.db.get_value("Sales Invoice", invoice_name, INVOICE_LIST_FIELDS, as_dict=True)
	row = _with_job_reference(row)
	row = _enrich_job_context([row])[0]
	row = _decorate_invoice_row(row, getdate(nowdate()))

	payment_history = frappe.db.sql(
		"""
		SELECT pe.posting_date, per.allocated_amount AS paid_amount, pe.mode_of_payment, pe.reference_no
		FROM `tabPayment Entry Reference` per
		INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
		WHERE per.reference_doctype = 'Sales Invoice'
			AND per.reference_name = %(invoice_name)s
			AND pe.docstatus = 1
		ORDER BY pe.posting_date DESC
		""",
		{"invoice_name": invoice_name},
		as_dict=True,
	)
	row["payment_history"] = payment_history

	log_portal_access(
		"view_invoice", doctype="Sales Invoice", docname=invoice_name, party_type="Customer", party=customer
	)

	return row


@frappe.whitelist()
def export_statement_of_account(format="pdf", party=None, from_date=None, to_date=None):
	"""Customer-scoped Statement of Account (Job Linked) export."""
	check_portal_access()
	customers = _caller_customer_filter()
	filters = _statement_filters(customers, party=party, from_date=from_date, to_date=to_date)

	export_format = (format or "pdf").lower()
	if export_format == "excel":
		filename, content = build_statement_job_linked_excel(filters)
		frappe.local.response.type = "binary"
	else:
		filename, content = build_statement_job_linked_pdf(filters)
		frappe.local.response.type = "download"

	frappe.local.response.filename = filename
	frappe.local.response.filecontent = content

	log_portal_access(
		"export_statement_of_account",
		party_type="Customer",
		party=filters.get("party"),
	)


@frappe.whitelist()
def download_invoice_pdf(invoice_name):
	check_portal_access()
	assert_customer_scope("Sales Invoice", invoice_name)

	# Cannot use frappe.utils.print_format.download_pdf directly: it calls
	# validate_print_permission() -> frappe.has_permission(), which always
	# fails for Customer Portal User (zero DocType permissions by design).
	# assert_customer_scope() above is the real access boundary here.
	doc = frappe.get_doc("Sales Invoice", invoice_name)
	frappe.local.flags.ignore_print_permissions = True
	try:
		html = frappe.get_print(
			"Sales Invoice",
			invoice_name,
			print_format="FreightMas Sales Invoice",
			doc=doc,
			as_pdf=False,
		)
	finally:
		frappe.local.flags.ignore_print_permissions = False
	html = portal_invoice_pdf_logo_injection(doc.company) + html
	pdf_file = frappe.utils.pdf.get_pdf(html)

	frappe.local.response.filename = f"{invoice_name.replace(' ', '-').replace('/', '-')}.pdf"
	frappe.local.response.filecontent = pdf_file
	frappe.local.response.type = "download"

	log_portal_access(
		"download_invoice_pdf", doctype="Sales Invoice", docname=invoice_name,
		party_type="Customer", party=doc.customer,
	)
