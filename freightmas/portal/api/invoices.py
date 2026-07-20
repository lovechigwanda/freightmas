# Client Portal read API: Sales Invoice list + detail + PDF download
# ("Invoices & Billing"). Mirrors freightmas.portal.supplier.invoices
# (Purchase Invoice) almost 1:1, swapped to Customer scope - see that
# module's header comment for why no child-row scoping is needed here.

import frappe
from frappe import _
from frappe.utils import get_year_start, getdate, nowdate

from freightmas.portal.security import assert_customer_scope, check_portal_access, get_portal_customer_names, log_portal_access

INVOICE_LIST_FIELDS = [
	"name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status",
	"is_forwarding_invoice", "forwarding_job_reference",
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


def _with_job_reference(row):
	job_doctype, job_name = None, None
	for flag, ref_field, label in JOB_REFERENCE_FLAGS:
		if row.get(flag) and row.get(ref_field):
			job_doctype, job_name = label, row.get(ref_field)
			break
	row["job_doctype"] = job_doctype
	row["job_name"] = job_name
	return row


def _caller_customer_filter():
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			_("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)
	return customers


@frappe.whitelist()
def get_invoices(status=None, limit_start=0, limit_page_length=20):
	check_portal_access()
	customers = _caller_customer_filter()

	filters = {"docstatus": ["<", 2], "customer": ["in", customers]}
	if status:
		filters["status"] = status

	# get_all(), not get_list(): Customer Portal User holds zero DocType
	# permissions by design (see freightmas/portal/security.py) - the
	# explicit `customer` filter above is the actual access boundary.
	invoices = frappe.get_all(
		"Sales Invoice",
		filters=filters,
		fields=INVOICE_LIST_FIELDS,
		order_by="posting_date desc",
		limit_start=frappe.utils.cint(limit_start),
		limit_page_length=frappe.utils.cint(limit_page_length),
	)
	total_count = frappe.db.count("Sales Invoice", filters=filters)

	invoices = [_with_job_reference(row) for row in invoices]

	party = customers[0] if len(customers) == 1 else None
	log_portal_access("list_invoices", doctype="Sales Invoice", party_type="Customer", party=party)

	return {"invoices": invoices, "total_count": total_count}


@frappe.whitelist()
def get_invoices_summary():
	"""KPI tiles for the Invoices list page: outstanding, overdue, paid YTD.

	Computed independently of any list-page status filter/pagination.
	"""
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
		"paid_ytd": paid_ytd,
	}


@frappe.whitelist()
def get_invoice_detail(invoice_name):
	check_portal_access()
	customer = assert_customer_scope("Sales Invoice", invoice_name)

	row = frappe.db.get_value("Sales Invoice", invoice_name, INVOICE_LIST_FIELDS, as_dict=True)
	row = _with_job_reference(row)

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
def download_invoice_pdf(invoice_name):
	check_portal_access()
	assert_customer_scope("Sales Invoice", invoice_name)

	# Cannot use frappe.utils.print_format.download_pdf directly: it calls
	# validate_print_permission() -> frappe.has_permission(), which always
	# fails for Customer Portal User (zero DocType permissions by design).
	# assert_customer_scope() above is the real access boundary here.
	doc = frappe.get_doc("Sales Invoice", invoice_name)
	pdf_file = frappe.get_print("Sales Invoice", invoice_name, doc=doc, as_pdf=True)

	frappe.local.response.filename = f"{invoice_name.replace(' ', '-').replace('/', '-')}.pdf"
	frappe.local.response.filecontent = pdf_file
	frappe.local.response.type = "pdf"

	log_portal_access(
		"download_invoice_pdf", doctype="Sales Invoice", docname=invoice_name,
		party_type="Customer", party=doc.customer,
	)
