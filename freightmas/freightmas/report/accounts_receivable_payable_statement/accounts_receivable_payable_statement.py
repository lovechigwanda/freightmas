# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    validate_filters(filters)

    party_type = filters.get("party_type", "Customer")
    columns = get_columns(party_type)
    data = get_data(filters)

    return columns, data


def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("party"):
        frappe.throw(_("Party is required"))


def get_columns(party_type):
    cn_label = _("Credit Note") if party_type == "Customer" else _("Debit Note")

    return [
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "voucher_type",
            "label": _("Voucher Type"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "voucher_no",
            "label": _("Voucher No"),
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180
        },
        {
            "fieldname": "invoiced_amount",
            "label": _("Invoiced Amount"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "paid_amount",
            "label": _("Paid Amount"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "credit_note",
            "label": cn_label,
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "outstanding",
            "label": _("Outstanding"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "remarks",
            "label": _("Remarks"),
            "fieldtype": "Data",
            "width": 300
        }
    ]


def get_data(filters):
    party_type = filters.get("party_type", "Customer")

    if party_type == "Customer":
        data = get_sales_invoices(filters)
    else:
        data = get_purchase_invoices(filters)

    process_rows(data)

    if not filters.get("show_fully_paid"):
        data = [row for row in data if flt(row.get("outstanding")) != 0]

    append_totals_row(data)

    return data


def get_sales_invoices(filters):
    docstatus_list = get_docstatus_list(filters)

    return frappe.db.sql("""
        SELECT
            si.posting_date,
            'Sales Invoice' as voucher_type,
            si.name as voucher_no,
            si.grand_total as invoiced_amount,
            si.docstatus,
            COALESCE(cn.credit_note_total, 0) as credit_note,
            si.outstanding_amount as outstanding,
            si.remarks
        FROM `tabSales Invoice` si
        LEFT JOIN (
            SELECT
                return_against,
                SUM(ABS(grand_total)) as credit_note_total
            FROM `tabSales Invoice`
            WHERE is_return = 1
            AND docstatus = 1
            GROUP BY return_against
        ) cn ON cn.return_against = si.name
        WHERE si.is_return = 0
        AND si.customer = %(party)s
        AND si.company = %(company)s
        AND si.docstatus IN ({docstatus})
        ORDER BY si.posting_date, si.name
    """.format(docstatus=docstatus_list), filters, as_dict=1)


def get_purchase_invoices(filters):
    docstatus_list = get_docstatus_list(filters)

    return frappe.db.sql("""
        SELECT
            pi.posting_date,
            'Purchase Invoice' as voucher_type,
            pi.name as voucher_no,
            pi.grand_total as invoiced_amount,
            pi.docstatus,
            COALESCE(dn.debit_note_total, 0) as credit_note,
            pi.outstanding_amount as outstanding,
            pi.remarks
        FROM `tabPurchase Invoice` pi
        LEFT JOIN (
            SELECT
                return_against,
                SUM(ABS(grand_total)) as debit_note_total
            FROM `tabPurchase Invoice`
            WHERE is_return = 1
            AND docstatus = 1
            GROUP BY return_against
        ) dn ON dn.return_against = pi.name
        WHERE pi.is_return = 0
        AND pi.supplier = %(party)s
        AND pi.company = %(company)s
        AND pi.docstatus IN ({docstatus})
        ORDER BY pi.posting_date, pi.name
    """.format(docstatus=docstatus_list), filters, as_dict=1)


def get_docstatus_list(filters):
    statuses = [1]
    if filters.get("include_draft_invoices"):
        statuses.append(0)
    if filters.get("include_cancelled"):
        statuses.append(2)
    return ", ".join(str(s) for s in statuses)


def process_rows(data):
    for row in data:
        docstatus = row.get("docstatus")

        if docstatus == 0:
            row["paid_amount"] = 0
            row["credit_note"] = 0
            row["outstanding"] = flt(row["invoiced_amount"])
            row["remarks"] = "[Draft] " + (row.get("remarks") or "")

        elif docstatus == 2:
            row["paid_amount"] = 0
            row["credit_note"] = 0
            row["outstanding"] = 0
            row["remarks"] = "[Cancelled] " + (row.get("remarks") or "")

        else:
            row["paid_amount"] = (
                flt(row["invoiced_amount"])
                - flt(row["credit_note"])
                - flt(row["outstanding"])
            )


def append_totals_row(data):
    totals = {
        "invoiced_amount": 0,
        "paid_amount": 0,
        "credit_note": 0,
        "outstanding": 0,
    }

    for row in data:
        if row.get("docstatus") != 2:
            for key in totals:
                totals[key] += flt(row.get(key, 0))

    data.append({
        "posting_date": "",
        "voucher_type": "",
        "voucher_no": "Total",
        "invoiced_amount": totals["invoiced_amount"],
        "paid_amount": totals["paid_amount"],
        "credit_note": totals["credit_note"],
        "outstanding": totals["outstanding"],
        "remarks": "",
        "is_total_row": True,
    })
