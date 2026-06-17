# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate

MAX_REMARKS_LENGTH = 120


def _truncate_remarks(text, max_len=MAX_REMARKS_LENGTH):
    if not text:
        return text
    text = str(text)
    return text if len(text) <= max_len else text[:max_len].rstrip() + "..."


def _truncate_payment_entry_remarks(text):
    """Keep only the first sentence — stop at the first '. ' or '.\n' not preceded by a digit."""
    if not text:
        return text
    import re
    text = str(text)
    match = re.search(r'(?<!\d)\.\s', text[10:])
    if match:
        return text[:10 + match.start() + 1]
    return text if len(text) <= 80 else text[:80].rstrip() + "..."


def _sort_entries_by_invoice_date(entries, party_type):
    """Sort GL entries so groups are ordered by invoice date, with invoice rows first per group."""
    from collections import defaultdict

    invoice_type = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"

    groups = defaultdict(list)
    for e in entries:
        groups[e["_ref_doc"]].append(e)

    unallocated = groups.pop("Unallocated", [])

    def anchor_date(group_entries):
        for e in group_entries:
            if e["voucher_type"] == invoice_type:
                return e["posting_date"]
        return min(e["posting_date"] for e in group_entries)

    sorted_groups = sorted(groups.items(), key=lambda g: anchor_date(g[1]))

    result = []
    for _ref, group in sorted_groups:
        invoices = sorted(
            [e for e in group if e["voucher_type"] == invoice_type],
            key=lambda e: e["posting_date"]
        )
        others = sorted(
            [e for e in group if e["voucher_type"] != invoice_type],
            key=lambda e: e["posting_date"]
        )
        result.extend(invoices)
        result.extend(others)

    result.extend(sorted(unallocated, key=lambda e: e["posting_date"]))
    return result


def execute(filters=None):
    filters = filters or {}
    if filters.get("party"):
        party = frappe.parse_json(filters.get("party"))
        filters["party"] = party if isinstance(party, list) else [party]
    if not filters.get("party"):
        return get_columns(), []
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
            "fieldname": "reference_doc",
            "label": _("Reference Doc"),
            "fieldtype": "Data",
            "width": 160,
            "align": "left"
        },
        {
            "fieldname": "job_id",
            "label": _("Job ID"),
            "fieldtype": "Data",
            "width": 120,
            "align": "left"
        },
        {
            "fieldname": "voucher_subtype",
            "label": _("Voucher Sub Type"),
            "fieldtype": "Data",
            "width": 130,
            "align": "left"
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
            "width": 340,
            "align": "left"
        }
    ]


def get_data(filters):
    data = []
    party_type = filters.get("party_type") or "Customer"

    show_opening = filters.get("show_opening_balance", 1)
    opening_balance = get_opening_balance(filters) if show_opening else 0
    balance = opening_balance

    if show_opening:
        data.append({
            "posting_date": formatdate(filters.get("from_date"), "dd-MMM-yy"),
            "reference_doc": "",
            "job_id": "",
            "voucher_type": "",
            "voucher_subtype": "",
            "voucher_no": "Opening Balance",
            "debit": opening_balance if opening_balance > 0 else 0,
            "credit": abs(opening_balance) if opening_balance < 0 else 0,
            "balance": opening_balance,
            "remarks": "",
            "cssClass": "opening-balance-row"
        })

    conditions, params = get_conditions(filters)

    gl_entries = frappe.db.sql("""
        SELECT
            posting_date,
            voucher_type,
            voucher_subtype,
            voucher_no,
            against_voucher_type,
            against_voucher,
            debit,
            credit,
            remarks
        FROM `tabGL Entry`
        WHERE party_type = %(party_type)s
        AND {conditions}
        AND is_cancelled = 0
        ORDER BY posting_date, creation
    """.format(conditions=conditions), params, as_dict=1)

    credit_note_map = build_credit_note_map(gl_entries)

    # Pass 1: attach reference_doc to each entry for grouping/sorting
    for entry in gl_entries:
        entry["_ref_doc"] = resolve_reference_doc(entry, credit_note_map, party_type)

    # Sort: groups ordered by invoice date, invoice rows first within each group
    gl_entries = _sort_entries_by_invoice_date(gl_entries, party_type)

    ref_docs = {e["_ref_doc"] for e in gl_entries}
    job_id_map = build_job_id_map(ref_docs, party_type)

    total_debit = 0.0
    total_credit = 0.0
    current_ref_doc = None
    group_index = 0

    # Pass 2: compute running balance in sorted order
    for entry in gl_entries:
        balance += (entry.debit - entry.credit)
        total_debit += entry.debit
        total_credit += entry.credit

        reference_doc = entry["_ref_doc"]

        if reference_doc != current_ref_doc:
            current_ref_doc = reference_doc
            group_index += 1

        css_class = "row-group-alt" if group_index % 2 == 0 else ""

        row = {
            "posting_date": formatdate(entry.posting_date, "dd-MMM-yy"),
            "reference_doc": reference_doc,
            "job_id": job_id_map.get(reference_doc, ""),
            "voucher_type": entry.voucher_type,
            "voucher_subtype": entry.voucher_subtype or entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "debit": entry.debit or 0,
            "credit": entry.credit or 0,
            "balance": balance,
            "remarks": _truncate_payment_entry_remarks(entry.remarks) if entry.voucher_type == "Payment Entry" else _truncate_remarks(entry.remarks),
            "cssClass": css_class
        }
        data.append(row)

    data.append({
        "posting_date": "",
        "reference_doc": "",
        "job_id": "",
        "voucher_type": "",
        "voucher_subtype": "",
        "voucher_no": "Totals",
        "debit": total_debit,
        "credit": total_credit,
        "balance": balance,
        "remarks": "",
        "bold": 1
    })

    _verify_closing_balance(filters, params, conditions, balance, opening_balance)

    return data


def resolve_reference_doc(entry, credit_note_map, party_type="Customer"):
    """Derive the Reference Doc column value for a GL Entry row."""
    vt = entry.voucher_type
    vn = entry.voucher_no
    av = entry.get("against_voucher") or ""
    av_type = entry.get("against_voucher_type") or ""
    invoice_type = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"

    if vt == invoice_type:
        if vn in credit_note_map:
            return credit_note_map[vn]
        return vn

    if vt in ("Payment Entry", "Journal Entry"):
        if av and av_type == invoice_type:
            return av
        return "Unallocated"

    if av:
        return av
    return vn


def build_credit_note_map(gl_entries):
    """Return {credit_note_name: return_against} for all Sales Invoice GL rows that are returns."""
    sinv_names = [
        e.voucher_no for e in gl_entries if e.voucher_type == "Sales Invoice"
    ]
    if not sinv_names:
        return {}

    rows = frappe.db.sql(
        """SELECT name, return_against FROM `tabSales Invoice`
           WHERE name IN %(names)s AND is_return = 1 AND return_against IS NOT NULL""",
        {"names": sinv_names},
        as_dict=1
    )
    return {r.name: r.return_against for r in rows}


def build_job_id_map(reference_docs, party_type):
    """Return {invoice_name: job_name} by querying charge tables for each job type."""
    invoices = tuple(d for d in reference_docs if d and d != "Unallocated")
    if not invoices:
        return {}

    params = {"invoices": invoices}
    result = {}

    if party_type == "Customer":
        queries = [
            "SELECT sales_invoice_reference AS inv, parent FROM `tabForwarding Revenue Charges` WHERE sales_invoice_reference IN %(invoices)s",
            "SELECT sales_invoice_reference AS inv, parent FROM `tabClearing Revenue Charges` WHERE sales_invoice_reference IN %(invoices)s",
            "SELECT sales_invoice_reference AS inv, parent FROM `tabBorder Clearing Revenue Charges` WHERE sales_invoice_reference IN %(invoices)s",
            "SELECT sales_invoice AS inv, parent FROM `tabTrip Revenue Charges` WHERE sales_invoice IN %(invoices)s",
            "SELECT sales_invoice AS inv, parent FROM `tabWarehouse Job Storage Charges` WHERE sales_invoice IN %(invoices)s",
            "SELECT sales_invoice AS inv, parent FROM `tabWarehouse Job Handling Charges` WHERE sales_invoice IN %(invoices)s",
            "SELECT sales_invoice AS inv, parent FROM `tabWarehouse Job Rental Charges` WHERE sales_invoice IN %(invoices)s",
        ]
    else:
        queries = [
            "SELECT purchase_invoice_reference AS inv, parent FROM `tabForwarding Cost Charges` WHERE purchase_invoice_reference IN %(invoices)s",
            "SELECT purchase_invoice_reference AS inv, parent FROM `tabClearing Cost Charges` WHERE purchase_invoice_reference IN %(invoices)s",
            "SELECT purchase_invoice_reference AS inv, parent FROM `tabBorder Clearing Cost Charges` WHERE purchase_invoice_reference IN %(invoices)s",
        ]

    for query in queries:
        for row in frappe.db.sql(query, params, as_dict=1):
            if row.inv and row.inv not in result:
                result[row.inv] = row.parent

    return result


def get_opening_balance(filters):
    params = {
        "party_type": filters.get("party_type"),
        "party": tuple(filters.get("party")),
        "company": filters.get("company"),
        "from_date": filters.get("from_date"),
    }
    account_cond = ""
    if filters.get("account"):
        params["account"] = filters.get("account")
        account_cond = "AND account = %(account)s"

    result = frappe.db.sql("""
        SELECT SUM(debit) - SUM(credit) as balance
        FROM `tabGL Entry`
        WHERE party_type = %(party_type)s
        AND party IN %(party)s
        AND company = %(company)s
        AND posting_date < %(from_date)s
        AND is_cancelled = 0
        {account_cond}
    """.format(account_cond=account_cond), params, as_dict=1)

    return (result[0].balance or 0) if result else 0


def get_conditions(filters):
    conditions = []
    params = {
        "party_type": filters.get("party_type"),
        "party": tuple(filters.get("party")),
        "company": filters.get("company"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
    }

    conditions.append("company = %(company)s")
    conditions.append("party IN %(party)s")

    if filters.get("from_date"):
        conditions.append("posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("posting_date <= %(to_date)s")
    if filters.get("account"):
        params["account"] = filters.get("account")
        conditions.append("account = %(account)s")

    return " AND ".join(conditions), params


def _verify_closing_balance(filters, params, conditions, closing_balance, opening_balance):
    """Log a warning if closing balance does not match the direct GL sum."""
    try:
        direct = frappe.db.sql("""
            SELECT SUM(debit) - SUM(credit) as net
            FROM `tabGL Entry`
            WHERE party_type = %(party_type)s
            AND {conditions}
            AND is_cancelled = 0
        """.format(conditions=conditions), params, as_dict=1)

        direct_net = (direct[0].net or 0) if direct else 0
        expected = opening_balance + direct_net

        if abs(closing_balance - expected) > 0.01:
            frappe.log_error(
                "Statement of Accounts (Allocation): closing balance mismatch. "
                "Report closing={}, Expected={}".format(closing_balance, expected),
                "Statement of Accounts Allocation Integrity"
            )
    except Exception:
        pass
