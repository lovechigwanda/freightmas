# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    conditions = "1=1 AND status != 'Cancelled'"
    if filters.get("from_date"):
        conditions += f" AND date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND date_created <= '{filters['to_date']}'"
    if filters.get("customer"):
        conditions += f" AND customer = '{filters['customer']}'"
    if filters.get("status"):
        conditions += f" AND status = '{filters['status']}'"

    jobs = frappe.db.sql(f"""
        SELECT name, date_created, customer, customer_reference, direction, status,
               total_quoted_revenue_base, total_quoted_cost_base, total_quoted_profit_base,
               total_working_revenue_base, total_working_cost, total_working_profit_base
        FROM `tabForwarding Job`
        WHERE {conditions}
        ORDER BY date_created DESC
    """, as_dict=True)

    for job in jobs:
        # Check if job is billed
        invoiced_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference = %s
        """, (job["name"]))[0][0] or 0

        invoiced_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference = %s
        """, (job["name"]))[0][0] or 0

        # Only include unbilled jobs
        if invoiced_revenue == 0 or invoiced_cost == 0:
            data.append({
                "name": job["name"],
                "date_created": format_date(job.get("date_created")),
                "customer": job.get("customer", ""),
                "customer_reference": job.get("customer_reference", ""),
                "direction": job.get("direction", ""),
                "status": job.get("status", ""),
                "quoted_revenue": job.get("total_quoted_revenue_base", 0),
                "quoted_cost": job.get("total_quoted_cost_base", 0),
                "quoted_profit": job.get("total_quoted_profit_base", 0),
                "working_revenue": job.get("total_working_revenue_base", 0),
                "working_cost": job.get("total_working_cost", 0),
                "working_profit": job.get("total_working_profit_base", 0),
            })

    return columns, data


def get_columns():
    return [
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 140},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": "Quoted Revenue", "fieldname": "quoted_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Quoted Cost", "fieldname": "quoted_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Quoted Profit", "fieldname": "quoted_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Working Revenue", "fieldname": "working_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Working Cost", "fieldname": "working_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Working Profit", "fieldname": "working_profit", "fieldtype": "Currency", "width": 120},
    ]


def format_date(date_str):
    """Format date string to dd-MMM-yy format."""
    if not date_str:
        return ""
    try:
        return formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str
