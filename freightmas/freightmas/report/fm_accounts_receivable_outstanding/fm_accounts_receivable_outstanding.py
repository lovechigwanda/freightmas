# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 250,
        },
        {
            "fieldname": "outstanding_submitted",
            "label": _("Outstanding (Submitted)"),
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "fieldname": "outstanding_draft",
            "label": _("Draft Invoices"),
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "fieldname": "total_outstanding",
            "label": _("Total Outstanding"),
            "fieldtype": "Currency",
            "width": 160,
        },
    ]


def get_data(filters):
    company = filters.get("company")
    customer = filters.get("customer")
    include_drafts = filters.get("include_draft_invoices")

    if not company:
        frappe.throw(_("Company filter is required"))

    conditions = ["gl.party_type = 'Customer'", "gl.is_cancelled = 0"]
    si_conditions = ["si.docstatus = 0", "si.is_return = 0"]

    if customer:
        conditions.append("gl.party = %(customer)s")
        si_conditions.append("si.customer = %(customer)s")

    params = {
        "company": company,
        "customer": customer,
    }

    # -----------------------------
    # 1. GL-based outstanding (submitted)
    # -----------------------------
    gl_data = frappe.db.sql(
        f"""
        SELECT
            gl.party AS customer,
            SUM(gl.debit) - SUM(gl.credit) AS outstanding_submitted
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE
            gl.company = %(company)s
            AND acc.account_type = 'Receivable'
            AND {" AND ".join(conditions)}
        GROUP BY gl.party
        """,
        params,
        as_dict=True,
    )

    gl_map = {row.customer: flt(row.outstanding_submitted) for row in gl_data}

    # -----------------------------
    # 2. Draft invoices (optional)
    # -----------------------------
    draft_map = {}

    if include_drafts:
        draft_data = frappe.db.sql(
            f"""
            SELECT
                si.customer,
                SUM(si.grand_total) AS outstanding_draft
            FROM `tabSales Invoice` si
            WHERE
                si.company = %(company)s
                AND {" AND ".join(si_conditions)}
            GROUP BY si.customer
            """,
            params,
            as_dict=True,
        )

        draft_map = {
            row.customer: flt(row.outstanding_draft) for row in draft_data
        }

    # -----------------------------
    # 3. Merge results
    # -----------------------------
    customers = set(gl_map.keys()) | set(draft_map.keys())
    result = []

    for cust in customers:
        submitted = gl_map.get(cust, 0)
        draft = draft_map.get(cust, 0) if include_drafts else 0
        total = submitted + draft

        if total != 0:
            result.append(
                {
                    "customer": cust,
                    "outstanding_submitted": submitted,
                    "outstanding_draft": draft,
                    "total_outstanding": total,
                }
            )

    # Sort by total outstanding descending
    result.sort(key=lambda x: (-x["total_outstanding"], x["customer"]))

    return result