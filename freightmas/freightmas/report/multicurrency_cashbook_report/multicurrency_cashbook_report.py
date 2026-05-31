# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import re
import frappe
from frappe import _
from frappe.utils import formatdate


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
            "fieldname": "voucher_no",
            "label": _("Voucher No"),
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 185,
            "align": "left"
        },
        {
            "fieldname": "remarks",
            "label": _("Remarks"),
            "fieldtype": "Text",
            "width": 400
        },
        {
            "fieldname": "debit",
            "label": _("Debit (Co. Currency)"),
            "fieldtype": "Currency",
            "width": 155
        },
        {
            "fieldname": "credit",
            "label": _("Credit (Co. Currency)"),
            "fieldtype": "Currency",
            "width": 155
        },
        {
            "fieldname": "balance",
            "label": _("Balance (Co. Currency)"),
            "fieldtype": "Currency",
            "width": 160
        },
        {
            "fieldname": "debit_in_account_currency",
            "label": _("Debit (Acct. Currency)"),
            "fieldtype": "Float",
            "width": 155
        },
        {
            "fieldname": "credit_in_account_currency",
            "label": _("Credit (Acct. Currency)"),
            "fieldtype": "Float",
            "width": 155
        },
        {
            "fieldname": "balance_in_account_currency",
            "label": _("Balance (Acct. Currency)"),
            "fieldtype": "Float",
            "width": 160
        },
        {
            "fieldname": "account_currency",
            "label": _("Acct. Currency"),
            "fieldtype": "Data",
            "width": 90
        }
    ]


def truncate_remarks(remarks):
    if not remarks:
        return remarks
    match = re.search(r'(.*?dated\s+\d{4}-\d{2}-\d{2})', remarks)
    if match:
        return match.group(1)
    return remarks


def get_data(filters):
    data = []

    opening = get_opening_balance(filters)
    balance = opening["balance"]
    balance_in_account_currency = opening["balance_in_account_currency"]

    data.append({
        "posting_date": formatdate(filters.get("from_date"), "dd-MMM-yy"),
        "voucher_no": "",
        "remarks": "Opening Balance",
        "debit": 0,
        "credit": 0,
        "balance": balance,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": 0,
        "balance_in_account_currency": balance_in_account_currency,
        "account_currency": ""
    })

    conditions = get_conditions(filters)

    gl_entries = frappe.db.sql("""
        SELECT
            posting_date,
            voucher_type,
            voucher_no,
            account,
            against,
            debit,
            credit,
            debit_in_account_currency,
            credit_in_account_currency,
            account_currency,
            remarks
        FROM `tabGL Entry`
        WHERE account in (
            SELECT name
            FROM tabAccount
            WHERE account_type in ('Bank', 'Cash')
        )
        AND {conditions}
        ORDER BY posting_date, creation
    """.format(conditions=conditions), filters, as_dict=1)

    for entry in gl_entries:
        balance += (entry.debit - entry.credit)
        balance_in_account_currency += (
            (entry.debit_in_account_currency or 0) - (entry.credit_in_account_currency or 0)
        )
        data.append({
            "posting_date": formatdate(entry.posting_date, "dd-MMM-yy"),
            "voucher_type": entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "remarks": truncate_remarks(entry.remarks),
            "debit": entry.debit,
            "credit": entry.credit,
            "balance": balance,
            "debit_in_account_currency": entry.debit_in_account_currency or 0,
            "credit_in_account_currency": entry.credit_in_account_currency or 0,
            "balance_in_account_currency": balance_in_account_currency,
            "account_currency": entry.account_currency or ""
        })

    data.append({
        "posting_date": formatdate(filters.get("to_date"), "dd-MMM-yy"),
        "voucher_no": "",
        "remarks": "Closing Balance",
        "debit": 0,
        "credit": 0,
        "balance": balance,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": 0,
        "balance_in_account_currency": balance_in_account_currency,
        "account_currency": ""
    })

    return data


def get_opening_balance(filters):
    cancelled_condition = "" if filters.get("show_cancelled") else "AND is_cancelled = 0"
    result = frappe.db.sql("""
        SELECT
            SUM(debit) - SUM(credit) as balance,
            SUM(debit_in_account_currency) - SUM(credit_in_account_currency) as balance_in_account_currency
        FROM `tabGL Entry`
        WHERE account in (
            SELECT name
            FROM tabAccount
            WHERE account_type in ('Bank', 'Cash')
        )
        AND posting_date < %(from_date)s
        AND company = %(company)s
        {account_condition}
        {cancelled_condition}
    """.format(
        account_condition="AND account=%(account)s" if filters.get("account") else "",
        cancelled_condition=cancelled_condition
    ), filters, as_dict=1)[0]

    return {
        "balance": result.balance or 0,
        "balance_in_account_currency": result.balance_in_account_currency or 0
    }


def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("company=%(company)s")
    if filters.get("from_date"):
        conditions.append("posting_date>=%(from_date)s")
    if filters.get("to_date"):
        conditions.append("posting_date<=%(to_date)s")
    if filters.get("account"):
        conditions.append("account=%(account)s")
    if not filters.get("show_cancelled"):
        conditions.append("is_cancelled = 0")

    return " AND ".join(conditions)
