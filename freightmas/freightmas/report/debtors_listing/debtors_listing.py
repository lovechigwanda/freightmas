# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}

    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Company is required"))

    if not filters.get("as_of_date"):
        frappe.throw(_("As of Date is required"))


def get_columns():
    return [
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 300,
        },
        {
            "fieldname": "balance",
            "label": _("Balance"),
            "fieldtype": "Currency",
            "width": 180,
        },
    ]


def get_data(filters):
    conditions = ["gl.party_type = 'Customer'", "gl.is_cancelled = 0"]

    if filters.get("customer"):
        conditions.append("gl.party = %(customer)s")

    params = {
        "company": filters.get("company"),
        "as_of_date": filters.get("as_of_date"),
        "customer": filters.get("customer"),
    }

    gl_data = frappe.db.sql(
        f"""
        SELECT
            gl.party AS customer,
            SUM(gl.debit) - SUM(gl.credit) AS balance
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE
            gl.company = %(company)s
            AND acc.account_type = 'Receivable'
            AND gl.posting_date <= %(as_of_date)s
            AND {" AND ".join(conditions)}
        GROUP BY gl.party
        HAVING balance != 0
        ORDER BY balance DESC, gl.party ASC
        """,
        params,
        as_dict=True,
    )

    return gl_data
