# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate

MAX_REMARKS_LENGTH = 120

# Job reference fields present on both Sales Invoice and Purchase Invoice
INVOICE_JOB_REF_FIELDS = [
    "forwarding_job_reference",
    "clearing_job_reference",
    "road_freight_job_reference",
    "border_clearing_job_reference",
    "warehouse_job_reference",
    "trip_reference",
]


def _truncate_remarks(text, max_len=MAX_REMARKS_LENGTH):
    if not text:
        return text
    text = str(text)
    return text if len(text) <= max_len else text[:max_len].rstrip() + "..."


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "voucher_type",
            "label": _("Voucher Type"),
            "fieldtype": "Data",
            "width": 130
        },
        {
            "fieldname": "voucher_no",
            "label": _("Voucher No"),
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 195,
            "align": "left"
        },
        {
            "fieldname": "job_id",
            "label": _("Job ID"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "debit",
            "label": _("Debit"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "credit",
            "label": _("Credit"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "balance",
            "label": _("Balance"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "remarks",
            "label": _("Remarks"),
            "fieldtype": "Text",
            "width": 300
        }
    ]


def get_data(filters):
    data = []

    opening_balance = get_opening_balance(filters)
    balance = opening_balance

    data.append({
        "posting_date": formatdate(filters.get("from_date"), "dd-MMM-yy"),
        "voucher_type": "Opening Balance",
        "voucher_no": "",
        "job_id": "",
        "debit": 0,
        "credit": 0,
        "balance": opening_balance,
        "remarks": "Opening Balance"
    })

    conditions = get_conditions(filters)

    gl_entries = frappe.db.sql("""
        SELECT
            posting_date,
            voucher_type,
            voucher_no,
            account,
            party,
            debit,
            credit,
            remarks
        FROM `tabGL Entry`
        WHERE party_type = %(party_type)s
        AND {conditions}
        ORDER BY posting_date, creation
    """.format(conditions=conditions), filters, as_dict=1)

    if filters.get("include_draft_invoices"):
        draft_invoices = get_draft_invoices(filters)
        all_entries = gl_entries + draft_invoices
        all_entries = sorted(all_entries, key=lambda x: x.posting_date)
    else:
        all_entries = gl_entries

    # Build job ID lookup maps for all GL entries in one batch
    invoice_job_map, payment_amount_job_map, payment_all_jobs_map = build_voucher_job_maps(all_entries)

    for entry in all_entries:
        balance += (entry.debit - entry.credit)
        job_id = resolve_job_id(entry, invoice_job_map, payment_amount_job_map, payment_all_jobs_map)
        row = {
            "posting_date": formatdate(entry.posting_date, "dd-MMM-yy"),
            "voucher_type": entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "job_id": job_id,
            "debit": entry.debit,
            "credit": entry.credit,
            "balance": balance,
            "remarks": _truncate_remarks(entry.remarks)
        }
        data.append(row)

    data.append({
        "posting_date": formatdate(filters.get("to_date"), "dd-MMM-yy"),
        "voucher_type": "Closing Balance",
        "voucher_no": "",
        "job_id": "",
        "debit": 0,
        "credit": 0,
        "balance": balance,
        "remarks": "Closing Balance"
    })

    return data


def resolve_job_id(entry, invoice_job_map, payment_amount_job_map, payment_all_jobs_map):
    """Return the job ID string for a GL entry row."""
    vt = entry.voucher_type
    vn = entry.voucher_no

    if vt in ("Sales Invoice", "Purchase Invoice"):
        return invoice_job_map.get(vn, "")

    if vt == "Payment Entry":
        amount = max(entry.get("debit") or 0, entry.get("credit") or 0)
        key = (vn, amount)
        if key in payment_amount_job_map:
            return payment_amount_job_map[key]
        # Fallback: show all jobs linked to this payment
        return payment_all_jobs_map.get(vn, "")

    return ""


def build_voucher_job_maps(gl_entries):
    """
    Build lookup maps for job IDs from GL entry vouchers.

    Returns:
        invoice_job_map: {voucher_no -> job_id} for Sales/Purchase Invoice GL entries
        payment_amount_job_map: {(payment_no, allocated_amount) -> job_id_string} for Payment Entries
        payment_all_jobs_map: {payment_no -> comma-separated job_ids} fallback for Payment Entries
    """
    sinv_set = set()
    pinv_set = set()
    payment_set = set()

    for entry in gl_entries:
        vt = entry.voucher_type
        vn = entry.voucher_no
        if vt == "Sales Invoice":
            sinv_set.add(vn)
        elif vt == "Purchase Invoice":
            pinv_set.add(vn)
        elif vt == "Payment Entry":
            payment_set.add(vn)

    invoice_job_map = {}

    if sinv_set:
        invoice_job_map.update(_fetch_invoice_job_ids("Sales Invoice", list(sinv_set)))

    if pinv_set:
        invoice_job_map.update(_fetch_invoice_job_ids("Purchase Invoice", list(pinv_set)))

    payment_amount_job_map = {}
    payment_all_jobs_map = {}

    if payment_set:
        payment_amount_job_map, payment_all_jobs_map = _build_payment_job_maps(list(payment_set))

    return invoice_job_map, payment_amount_job_map, payment_all_jobs_map


def _fetch_invoice_job_ids(doctype, names):
    """Batch-fetch job IDs for a list of invoice names. Returns {name -> job_id}."""
    if not names:
        return {}

    table = "tabSales Invoice" if doctype == "Sales Invoice" else "tabPurchase Invoice"
    ref_fields = ", ".join(INVOICE_JOB_REF_FIELDS)

    rows = frappe.db.sql(
        f"SELECT name, {ref_fields} FROM `{table}` WHERE name IN %(names)s",
        {"names": names},
        as_dict=1
    )

    result = {}
    for row in rows:
        for field in INVOICE_JOB_REF_FIELDS:
            if row.get(field):
                result[row.name] = row[field]
                break
    return result


def _build_payment_job_maps(payment_nos):
    """
    For a list of Payment Entry names, build:
      - amount_map: {(payment_no, allocated_amount) -> job_id_string}
      - all_jobs_map: {payment_no -> comma-separated job_ids}
    """
    refs = frappe.db.sql("""
        SELECT parent, reference_doctype, reference_name, allocated_amount
        FROM `tabPayment Entry Reference`
        WHERE parent IN %(parents)s
        AND reference_doctype IN ('Sales Invoice', 'Purchase Invoice')
    """, {"parents": payment_nos}, as_dict=1)

    if not refs:
        return {}, {}

    # Collect invoice names per doctype
    sinv_names = set()
    pinv_names = set()
    for ref in refs:
        if ref.reference_doctype == "Sales Invoice":
            sinv_names.add(ref.reference_name)
        elif ref.reference_doctype == "Purchase Invoice":
            pinv_names.add(ref.reference_name)

    # Fetch job IDs for all referenced invoices
    inv_job_map = {}
    if sinv_names:
        inv_job_map.update(_fetch_invoice_job_ids("Sales Invoice", list(sinv_names)))
    if pinv_names:
        inv_job_map.update(_fetch_invoice_job_ids("Purchase Invoice", list(pinv_names)))

    # Build (payment_no, amount) -> job_ids and payment_no -> all job_ids maps
    amount_map = {}   # (payment_no, amount) -> set of job_ids
    all_jobs = {}     # payment_no -> set of job_ids

    for ref in refs:
        job_id = inv_job_map.get(ref.reference_name)
        if not job_id:
            continue

        pno = ref.parent
        amt = ref.allocated_amount

        all_jobs.setdefault(pno, set()).add(job_id)
        amount_map.setdefault((pno, amt), set()).add(job_id)

    # Convert sets to sorted comma-separated strings
    return (
        {k: ", ".join(sorted(v)) for k, v in amount_map.items()},
        {k: ", ".join(sorted(v)) for k, v in all_jobs.items()},
    )


def get_opening_balance(filters):
    cancelled_condition = "" if filters.get("include_cancelled") else "AND is_cancelled = 0"
    balance = frappe.db.sql("""
        SELECT SUM(debit) - SUM(credit) as balance
        FROM `tabGL Entry`
        WHERE party_type = %(party_type)s
        AND posting_date < %(from_date)s
        AND company = %(company)s
        AND party = %(party)s
        {cancelled_condition}
    """.format(cancelled_condition=cancelled_condition), filters, as_dict=1)[0].balance

    return balance or 0


def get_draft_invoices(filters):
    if filters.get("party_type") == "Customer":
        return get_draft_sales_invoices(filters)
    else:
        return get_draft_purchase_invoices(filters)


def get_draft_sales_invoices(filters):
    return frappe.db.sql("""
        SELECT
            posting_date,
            'Sales Invoice' as voucher_type,
            name as voucher_no,
            '' as account,
            customer as party,
            grand_total as debit,
            0 as credit,
            CONCAT('Draft Invoice - ', name) as remarks
        FROM `tabSales Invoice`
        WHERE docstatus = 0
        AND customer = %(party)s
        AND company = %(company)s
        AND posting_date >= %(from_date)s
        AND posting_date <= %(to_date)s
    """, filters, as_dict=1)


def get_draft_purchase_invoices(filters):
    return frappe.db.sql("""
        SELECT
            posting_date,
            'Purchase Invoice' as voucher_type,
            name as voucher_no,
            '' as account,
            supplier as party,
            0 as debit,
            grand_total as credit,
            CONCAT('Draft Invoice - ', name) as remarks
        FROM `tabPurchase Invoice`
        WHERE docstatus = 0
        AND supplier = %(party)s
        AND company = %(company)s
        AND posting_date >= %(from_date)s
        AND posting_date <= %(to_date)s
    """, filters, as_dict=1)


def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("company = %(company)s")
    if filters.get("from_date"):
        conditions.append("posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("posting_date <= %(to_date)s")
    if filters.get("party"):
        conditions.append("party = %(party)s")
    if not filters.get("include_cancelled"):
        conditions.append("is_cancelled = 0")

    return " AND ".join(conditions)
