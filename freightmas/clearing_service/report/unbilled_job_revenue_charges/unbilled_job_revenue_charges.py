# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe.utils import fmt_money

# ----------------------------------------
# Main Report Execution
# ----------------------------------------

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build filter conditions
    conditions = "1=1"
    if filters.get("from_date"):
        conditions += f" AND cj.date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND cj.date_created <= '{filters['to_date']}'"
    if filters.get("job_no"):
        conditions += f" AND cj.name = '{filters['job_no']}'"
    if filters.get("currency"):
        conditions += f" AND cj.currency = '{filters['currency']}'"

    # Get company base currency
    base_currency = frappe.get_cached_value("Company", frappe.defaults.get_user_default("company"), "default_currency")

    # Query uninvoiced charges
    rows = frappe.db.sql(f"""
        SELECT
            cj.name AS job_no,
            cj.date_created,
            rc.customer,
            rc.charge,
            rc.description,
            rc.qty,
            rc.sell_rate,
            cj.currency,
            cj.conversion_rate,
            (rc.qty * rc.sell_rate) AS amount,
            (rc.qty * rc.sell_rate * cj.conversion_rate) AS base_amount
        FROM `tabClearing Job` cj
        JOIN `tabClearing Charges` rc ON rc.parent = cj.name
        WHERE rc.sell_rate > 0
        AND (rc.is_invoiced = 0 OR rc.is_invoiced IS NULL)
        AND {conditions}
        ORDER BY cj.name, cj.date_created
    """, as_dict=True)

    # Group charges by job and add totals
    grouped = {}
    for row in rows:
        grouped.setdefault(row.job_no, []).append(row)

    for job_no, charges in grouped.items():
        job_total = 0
        for row in charges:
            job_total += row.base_amount or 0
            data.append([
                row.job_no,
                row.date_created,
                row.customer,
                row.charge,
                row.description,
                fmt_money(row.amount, currency=row.currency),
                fmt_money(row.base_amount, currency=base_currency)
            ])
        # Total row (bold and indented)
        data.append([
            "", "", "", "", f"&nbsp;&nbsp;<b>Total for {job_no}</b>", "", f"<b>{fmt_money(job_total, currency=base_currency)}</b>"
        ])

    return columns, data

# ----------------------------------------
# Report Column Definitions
# ----------------------------------------

def get_columns():
    return [
        {"label": "Job No", "fieldname": "job_no", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Date", "width": 110},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Charge", "fieldname": "charge", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 240},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Data", "width": 140, "align": "right"},
        {"label": "Amount (Base)", "fieldname": "base_amount", "fieldtype": "Data", "width": 140, "align": "right"},
    ]

# ----------------------------------------
# Dynamic Filter: Job No (Only with uninvoiced charges)
# ----------------------------------------

@frappe.whitelist()
def get_job_nos_with_uninvoiced_charges(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""
        SELECT DISTINCT cj.name
        FROM `tabClearing Job` cj
        JOIN `tabClearing Charges` rc ON rc.parent = cj.name
        WHERE rc.sell_rate > 0 AND (rc.is_invoiced = 0 OR rc.is_invoiced IS NULL)
        AND cj.name LIKE %(txt)s
        ORDER BY cj.name DESC
        LIMIT 20
    """, {"txt": f"%{txt}%"})

# ----------------------------------------
# Dynamic Filter: Currency (Only for jobs with uninvoiced charges)
# ----------------------------------------

@frappe.whitelist()
def get_currencies_with_uninvoiced_charges(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""
        SELECT DISTINCT cj.currency
        FROM `tabClearing Job` cj
        JOIN `tabClearing Charges` rc ON rc.parent = cj.name
        WHERE rc.sell_rate > 0 AND (rc.is_invoiced = 0 OR rc.is_invoiced IS NULL)
        AND cj.currency LIKE %(txt)s
        ORDER BY cj.currency ASC
        LIMIT 20
    """, {"txt": f"%{txt}%"})