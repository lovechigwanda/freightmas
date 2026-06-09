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


def execute(filters=None):
    filters = filters or {}
    filters["party_type"] = "Customer"
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
            "width": 160
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
            "width": 340
        }
    ]


def get_data(filters):
    data = []

    show_opening = filters.get("show_opening_balance", 1)
    opening_balance = get_opening_balance(filters) if show_opening else 0
    balance = opening_balance

    if show_opening:
        data.append({
            "posting_date": formatdate(filters.get("from_date"), "dd-MMM-yy"),
            "reference_doc": "",
            "voucher_type": "",
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

    # Batch-build lookups to avoid N+1 queries
    credit_note_map = build_credit_note_map(gl_entries)

    total_debit = 0.0
    total_credit = 0.0

    # Track group colour alternation
    current_ref_doc = None
    group_index = 0

    for entry in gl_entries:
        balance += (entry.debit - entry.credit)
        total_debit += entry.debit
        total_credit += entry.credit

        reference_doc = resolve_reference_doc(entry, credit_note_map)

        if reference_doc != current_ref_doc:
            current_ref_doc = reference_doc
            group_index += 1

        css_class = "row-group-alt" if group_index % 2 == 0 else ""

        row = {
            "posting_date": formatdate(entry.posting_date, "dd-MMM-yy"),
            "reference_doc": reference_doc,
            "voucher_type": entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "debit": entry.debit or 0,
            "credit": entry.credit or 0,
            "balance": balance,
            "remarks": _truncate_remarks(entry.remarks),
            "cssClass": css_class
        }
        data.append(row)

    # Totals row
    data.append({
        "posting_date": "",
        "reference_doc": "",
        "voucher_type": "",
        "voucher_no": "Totals",
        "debit": total_debit,
        "credit": total_credit,
        "balance": balance,
        "remarks": "",
        "bold": 1
    })

    # Integrity check: closing balance must equal direct GL sum + opening balance
    _verify_closing_balance(filters, params, conditions, balance, opening_balance)

    return data


def resolve_reference_doc(entry, credit_note_map):
    """Derive the Reference Doc column value for a GL Entry row."""
    vt = entry.voucher_type
    vn = entry.voucher_no
    av = entry.get("against_voucher") or ""
    av_type = entry.get("against_voucher_type") or ""

    if vt == "Sales Invoice":
        # Credit notes have return_against set
        if vn in credit_note_map:
            return credit_note_map[vn]
        return vn

    if vt in ("Payment Entry", "Journal Entry"):
        if av and av_type == "Sales Invoice":
            return av
        return "Unallocated"

    # Fallback for other voucher types
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


def get_opening_balance(filters):
    params = {
        "party_type": filters.get("party_type"),
        "party": filters.get("party"),
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
        AND party = %(party)s
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
        "party": filters.get("party"),
        "company": filters.get("company"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
    }

    conditions.append("company = %(company)s")
    conditions.append("party = %(party)s")

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
