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
            "fieldname": "supplier",
            "label": _("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
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
    supplier = filters.get("supplier")
    include_drafts = filters.get("include_draft_invoices")

    if not company:
        frappe.throw(_("Company filter is required"))

    conditions = ["gl.party_type = 'Supplier'", "gl.is_cancelled = 0"]
    pi_conditions = ["pi.docstatus = 0", "pi.is_return = 0"]

    if supplier:
        conditions.append("gl.party = %(supplier)s")
        pi_conditions.append("pi.supplier = %(supplier)s")

    params = {
        "company": company,
        "supplier": supplier,
    }

    # -----------------------------
    # 1. GL-based outstanding (submitted)
    # -----------------------------
    gl_data = frappe.db.sql(
        f"""
        SELECT
            gl.party AS supplier,
            SUM(gl.credit) - SUM(gl.debit) AS outstanding_submitted
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE
            gl.company = %(company)s
            AND acc.account_type = 'Payable'
            AND {" AND ".join(conditions)}
        GROUP BY gl.party
        """,
        params,
        as_dict=True,
    )

    gl_map = {row.supplier: flt(row.outstanding_submitted) for row in gl_data}

    # -----------------------------
    # 2. Draft invoices (optional)
    # -----------------------------
    draft_map = {}

    if include_drafts:
        draft_data = frappe.db.sql(
            f"""
            SELECT
                pi.supplier,
                SUM(pi.grand_total) AS outstanding_draft
            FROM `tabPurchase Invoice` pi
            WHERE
                pi.company = %(company)s
                AND {" AND ".join(pi_conditions)}
            GROUP BY pi.supplier
            """,
            params,
            as_dict=True,
        )

        draft_map = {
            row.supplier: flt(row.outstanding_draft) for row in draft_data
        }

    # -----------------------------
    # 3. Merge results
    # -----------------------------
    suppliers = set(gl_map.keys()) | set(draft_map.keys())
    result = []

    for supp in suppliers:
        submitted = gl_map.get(supp, 0)
        draft = draft_map.get(supp, 0) if include_drafts else 0
        total = submitted + draft

        if total != 0:
            result.append(
                {
                    "supplier": supp,
                    "outstanding_submitted": submitted,
                    "outstanding_draft": draft,
                    "total_outstanding": total,
                }
            )

    # Sort by total outstanding descending
    result.sort(key=lambda x: (-x["total_outstanding"], x["supplier"]))

    return result
