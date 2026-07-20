# Supplier Portal read API: Purchase Invoice list + detail ("My Billing").
#
# Purchase Invoice's `supplier` field is a direct parent-level field, unlike
# the job charge-line case in supplier_scope.py, so the plain generalized
# assert_supplier_scope() is sufficient here - no child-row scoping needed.

import frappe

from freightmas.portal.security import SUPPLIER_PORTAL_ROLE, assert_supplier_scope, check_portal_access, log_portal_access
from freightmas.portal.supplier.jobs import _caller_supplier_filter

INVOICE_LIST_FIELDS = [
	"name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status",
	"is_forwarding_invoice", "forwarding_job_reference",
	"is_clearing_invoice", "clearing_job_reference",
	"is_border_clearing_invoice", "border_clearing_job_reference",
	"is_road_freight_invoice", "road_freight_job_reference",
	"is_warehouse_invoice", "warehouse_job_reference",
	"is_trip_invoice", "trip_reference",
]

# (is_flag_fieldname, job_reference_fieldname, job_doctype label) - used to
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


@frappe.whitelist()
def get_invoices(status=None, limit_start=0, limit_page_length=20):
	check_portal_access(role=SUPPLIER_PORTAL_ROLE)
	suppliers = _caller_supplier_filter()

	filters = {"docstatus": ["<", 2], "supplier": ["in", suppliers]}
	if status:
		filters["status"] = status

	invoices = frappe.get_all(
		"Purchase Invoice",
		filters=filters,
		fields=INVOICE_LIST_FIELDS,
		order_by="posting_date desc",
		limit_start=frappe.utils.cint(limit_start),
		limit_page_length=frappe.utils.cint(limit_page_length),
	)
	total_count = frappe.db.count("Purchase Invoice", filters=filters)

	invoices = [_with_job_reference(row) for row in invoices]

	party = suppliers[0] if len(suppliers) == 1 else None
	log_portal_access("list_invoices", doctype="Purchase Invoice", party_type="Supplier", party=party)

	return {"invoices": invoices, "total_count": total_count}


@frappe.whitelist()
def get_invoice_detail(invoice_name):
	check_portal_access(role=SUPPLIER_PORTAL_ROLE)
	supplier = assert_supplier_scope("Purchase Invoice", invoice_name, "supplier")

	row = frappe.db.get_value("Purchase Invoice", invoice_name, INVOICE_LIST_FIELDS, as_dict=True)
	row = _with_job_reference(row)

	log_portal_access(
		"view_invoice", doctype="Purchase Invoice", docname=invoice_name, party_type="Supplier", party=supplier
	)

	return row
