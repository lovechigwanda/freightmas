# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    if not filters:
        filters = {}

    validate_filters(filters)

    columns = get_columns(filters)
    data = get_data(filters)
    report_summary = get_report_summary(data)

    return columns, data, None, None, report_summary


# ----------------------------------------
# Validation
# ----------------------------------------

def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Company is required"))

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required"))

    if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
        frappe.throw(_("From Date cannot be after To Date"))

    if filters.get("party") and not filters.get("party_type"):
        frappe.throw(_("Please select Party Type before selecting Party"))


# ----------------------------------------
# Columns
# ----------------------------------------

def get_columns(filters):
    currency = get_currency(filters)
    return [
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 200,
        },
        {
            "label": _("Remarks"),
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Party Type"),
            "fieldname": "party_type",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Party"),
            "fieldname": "party",
            "fieldtype": "Dynamic Link",
            "options": "party_type",
            "width": 180,
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 160,
        },
        {
            "label": _("Debit ({0})").format(currency),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 130,
        },
        {
            "label": _("Credit ({0})").format(currency),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 130,
        },
        {
            "label": _("Net Indirect Expense ({0})").format(currency),
            "fieldname": "net_expense",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 140,
        },
    ]


# ----------------------------------------
# Data
# ----------------------------------------

def get_data(filters):
    conditions = get_conditions(filters)
    gl_entries = get_gl_entries(conditions, filters)

    if not gl_entries:
        return []

    return build_flat_data(gl_entries)


def get_gl_entries(conditions, filters):
    params = dict(filters)
    params.pop("group_by", None)
    params.pop("fiscal_year", None)

    query = """
        SELECT
            gle.posting_date,
            gle.account,
            acc.account_name,
            gle.cost_center,
            gle.party_type,
            gle.party,
            gle.voucher_type,
            gle.voucher_no,
            gle.debit,
            gle.credit,
            (gle.debit - gle.credit) AS net_expense,
            gle.remarks
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE acc.account_type = 'Indirect Expense'
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
            {conditions}
        ORDER BY gle.account, gle.posting_date, gle.voucher_no
    """.format(conditions=conditions)

    return frappe.db.sql(query, params, as_dict=True)


def get_conditions(filters):
    conditions = ""

    if filters.get("cost_center"):
        conditions += " AND gle.cost_center = %(cost_center)s"

    if filters.get("account"):
        conditions += " AND gle.account = %(account)s"

    if filters.get("party_type"):
        conditions += " AND gle.party_type = %(party_type)s"

    if filters.get("party"):
        conditions += " AND gle.party = %(party)s"

    if filters.get("voucher_type"):
        conditions += " AND gle.voucher_type = %(voucher_type)s"

    return conditions


# ----------------------------------------
# Build Flat Data
# ----------------------------------------

def build_flat_data(gl_entries):
    from freightmas.freightmas.report.report_export_utils import truncate_remarks

    data = []
    total_debit = 0
    total_credit = 0
    total_net = 0

    for entry in gl_entries:
        data.append({
            "posting_date": entry.posting_date,
            "account": entry.account,
            "account_name": entry.account_name,
            "cost_center": entry.cost_center,
            "party_type": entry.party_type,
            "party": entry.party,
            "voucher_type": entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "debit": flt(entry.debit, 2),
            "credit": flt(entry.credit, 2),
            "net_expense": flt(entry.net_expense, 2),
            "remarks": truncate_remarks(entry.remarks),
        })
        total_debit += flt(entry.debit, 2)
        total_credit += flt(entry.credit, 2)
        total_net += flt(entry.net_expense, 2)

    # Grand total row
    data.append({
        "posting_date": None,
        "account": "",
        "account_name": "Grand Total",
        "remarks": "<b>Grand Total</b>",
        "voucher_no": "",
        "debit": flt(total_debit, 2),
        "credit": flt(total_credit, 2),
        "net_expense": flt(total_net, 2),
        "is_group_total": 1,
    })

    return data


# ----------------------------------------
# Report Summary
# ----------------------------------------

def get_report_summary(data):
    if not data:
        return []

    grand_total_row = None
    for row in reversed(data):
        if row.get("is_group_total"):
            label = row.get("remarks", "") or row.get("account_name", "")
            if "Grand Total" in str(label):
                grand_total_row = row
                break

    if not grand_total_row:
        return []

    total_debit = flt(grand_total_row.get("debit", 0), 2)
    total_credit = flt(grand_total_row.get("credit", 0), 2)
    net_expense = flt(grand_total_row.get("net_expense", 0), 2)
    transaction_count = sum(1 for row in data if row.get("voucher_no") and not row.get("is_group_total"))

    return [
        {
            "value": total_debit,
            "indicator": "Red",
            "label": _("Total Indirect Expenses (Debit)"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": total_credit,
            "indicator": "Green",
            "label": _("Reversals / Adjustments (Credit)"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": net_expense,
            "indicator": "Orange",
            "label": _("Net Indirect Expenses"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": transaction_count,
            "indicator": "Grey",
            "label": _("Transactions"),
            "datatype": "Int",
        },
    ]


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
        report_title="Indirect Expenses Detail Report",
        net_field_label="Net Indirect Expenses",
    )
    send_excel_response(file_bytes, "Indirect_Expenses_Detail_Report.xlsx")


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
        report_title="Indirect Expenses Detail Report",
        net_fieldname="net_expense",
    )
    send_pdf_response(file_bytes, "Indirect_Expenses_Detail_Report.pdf")
