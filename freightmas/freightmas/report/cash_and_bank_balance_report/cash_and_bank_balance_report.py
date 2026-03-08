# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate


def execute(filters=None):
    if not filters:
        filters = {}

    validate_filters(filters)

    columns = get_columns(filters)
    data = get_data(filters)
    report_summary = get_report_summary(data, filters)
    chart = get_chart(data, filters)

    return columns, data, None, chart, report_summary


# ----------------------------------------
# Validation
# ----------------------------------------

def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Company is required"))

    if not filters.get("as_of_date"):
        frappe.throw(_("As of Date is required"))


# ----------------------------------------
# Columns
# ----------------------------------------

def get_columns(filters):
    currency = get_currency(filters)
    return [
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 250,
        },
        {
            "label": _("Account Type"),
            "fieldname": "account_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Balance ({0})").format(currency),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 180,
        },
        {
            "label": _("% of Total"),
            "fieldname": "percent_of_total",
            "fieldtype": "Percent",
            "width": 120,
        },
    ]


# ----------------------------------------
# Data
# ----------------------------------------

def get_data(filters):
    conditions = ""
    if filters.get("account"):
        conditions += " AND gle.account = %(account)s"

    balances = frappe.db.sql(
        """
        SELECT
            gle.account,
            acc.account_name,
            acc.account_type,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE acc.root_type = 'Asset'
            AND acc.account_type IN ('Cash', 'Bank')
            AND gle.company = %(company)s
            AND gle.posting_date <= %(as_of_date)s
            AND gle.is_cancelled = 0
            {conditions}
        GROUP BY gle.account, acc.account_name, acc.account_type
        ORDER BY acc.account_type, acc.account_name
        """.format(conditions=conditions),
        filters,
        as_dict=True,
    )

    if not balances:
        return []

    grand_total = sum(flt(row.balance, 2) for row in balances)

    data = []
    for row in balances:
        balance = flt(row.balance, 2)
        data.append({
            "account": row.account,
            "account_name": row.account_name,
            "account_type": row.account_type,
            "balance": balance,
            "percent_of_total": flt(balance / grand_total * 100, 2) if grand_total else 0,
        })

    # Grand total row
    data.append({
        "account": "",
        "account_name": "Total",
        "account_type": "",
        "balance": flt(grand_total, 2),
        "percent_of_total": 100.0 if grand_total else 0,
        "is_total_row": 1,
    })

    return data


# ----------------------------------------
# Report Summary
# ----------------------------------------

def get_report_summary(data, filters):
    if not data:
        return []

    cash_total = 0
    bank_total = 0

    for row in data:
        if row.get("is_total_row"):
            continue
        if row.get("account_type") == "Cash":
            cash_total += flt(row.get("balance", 0), 2)
        elif row.get("account_type") == "Bank":
            bank_total += flt(row.get("balance", 0), 2)

    combined = flt(cash_total + bank_total, 2)

    return [
        {
            "value": cash_total,
            "indicator": "Orange",
            "label": _("Total Cash Balance"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": bank_total,
            "indicator": "Blue",
            "label": _("Total Bank Balance"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": combined,
            "indicator": "Green",
            "label": _("Combined Total"),
            "datatype": "Currency",
            "currency": None,
        },
    ]


# ----------------------------------------
# Chart
# ----------------------------------------

def get_chart(data, filters):
    if not data:
        return None

    labels = []
    values = []

    for row in data:
        if row.get("is_total_row"):
            continue
        label = row.get("account_name") or row.get("account") or "Unknown"
        balance = flt(row.get("balance", 0), 2)
        if balance != 0:
            labels.append(label)
            values.append(balance)

    if not labels:
        return None

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Balance"),
                    "values": values,
                }
            ],
        },
        "type": "bar",
        "colors": ["#36a2eb"],
        "barOptions": {"spaceRatio": 0.4},
    }


# ----------------------------------------
# Utilities
# ----------------------------------------

def get_currency(filters):
    if filters.get("company"):
        return frappe.get_cached_value("Company", filters["company"], "default_currency")
    return frappe.defaults.get_global_default("currency") or "USD"


# ----------------------------------------
# Excel & PDF Export
# ----------------------------------------

@frappe.whitelist()
def export_excel(filters):
    """Generate and download a formatted Excel report."""
    import json
    if isinstance(filters, str):
        filters = json.loads(filters)

    validate_filters(filters)
    columns = get_columns(filters)
    data = get_data(filters)

    from freightmas.freightmas.report.report_export_utils import build_excel_file, send_excel_response

    file_bytes = build_excel_file(
        filters=filters,
        data=data,
        columns=columns,
        report_title="Cash and Bank Balance Report",
        net_field_label="Balance",
    )
    send_excel_response(file_bytes, "Cash_and_Bank_Balance_Report.xlsx")


@frappe.whitelist()
def export_pdf(filters):
    """Generate and download a formatted PDF report."""
    import json
    if isinstance(filters, str):
        filters = json.loads(filters)

    validate_filters(filters)
    columns = get_columns(filters)
    data = get_data(filters)

    from freightmas.freightmas.report.report_export_utils import build_pdf_file, send_pdf_response

    file_bytes = build_pdf_file(
        filters=filters,
        data=data,
        columns=columns,
        report_title="Cash and Bank Balance Report",
        net_fieldname="balance",
    )
    send_pdf_response(file_bytes, "Cash_and_Bank_Balance_Report.pdf")
