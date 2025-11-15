# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    conditions = "1=1 AND docstatus IN (0, 1)"
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
               total_quoted_revenue_base, total_quoted_cost_base, total_quoted_profit_base, quoted_margin_percent,
               total_working_revenue_base, total_working_cost, total_working_profit_base, profit_margin_percent
        FROM `tabForwarding Job`
        WHERE {conditions}
        ORDER BY date_created DESC
    """, as_dict=True)

    for job in jobs:
        # Quoted figures
        quoted_revenue = job.get("total_quoted_revenue_base", 0)
        quoted_cost = job.get("total_quoted_cost_base", 0)
        quoted_profit = job.get("total_quoted_profit_base", 0)
        quoted_margin = job.get("quoted_margin_percent", 0)
        
        # Working figures
        working_revenue = job.get("total_working_revenue_base", 0)
        working_cost = job.get("total_working_cost", 0)
        working_profit = job.get("total_working_profit_base", 0)
        working_margin = job.get("profit_margin_percent", 0)
        
        # Invoiced Revenue (Sales Invoice)
        invoiced_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference = %s
        """, (job["name"]))[0][0] or 0
        
        # Invoiced Cost (Purchase Invoice)
        invoiced_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference = %s
        """, (job["name"]))[0][0] or 0
        
        # Invoiced Profit & Margin
        invoiced_profit = invoiced_revenue - invoiced_cost
        invoiced_margin = (invoiced_profit / invoiced_revenue * 100) if invoiced_revenue else 0
        
        # Variance Analysis
        revenue_variance = invoiced_revenue - quoted_revenue
        cost_variance = invoiced_cost - quoted_cost
        profit_variance = invoiced_profit - quoted_profit

        data.append({
            "name": job["name"],
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "direction": job.get("direction", ""),
            "status": job.get("status", ""),
            "quoted_revenue": quoted_revenue,
            "quoted_cost": quoted_cost,
            "quoted_profit": quoted_profit,
            "quoted_margin": quoted_margin,
            "working_revenue": working_revenue,
            "working_cost": working_cost,
            "working_profit": working_profit,
            "working_margin": working_margin,
            "invoiced_revenue": invoiced_revenue,
            "invoiced_cost": invoiced_cost,
            "invoiced_profit": invoiced_profit,
            "invoiced_margin": invoiced_margin,
            "revenue_variance": revenue_variance,
            "cost_variance": cost_variance,
            "profit_variance": profit_variance,
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
        # Quoted Charges
        {"label": "Quoted Revenue", "fieldname": "quoted_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Quoted Cost", "fieldname": "quoted_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Quoted Profit", "fieldname": "quoted_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Quoted Margin %", "fieldname": "quoted_margin", "fieldtype": "Percent", "width": 100},
        # Working Charges
        {"label": "Working Revenue", "fieldname": "working_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Working Cost", "fieldname": "working_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Working Profit", "fieldname": "working_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Working Margin %", "fieldname": "working_margin", "fieldtype": "Percent", "width": 100},
        # Invoiced Charges
        {"label": "Invoiced Revenue", "fieldname": "invoiced_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Invoiced Cost", "fieldname": "invoiced_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Invoiced Profit", "fieldname": "invoiced_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Invoiced Margin %", "fieldname": "invoiced_margin", "fieldtype": "Percent", "width": 100},
        # Variance Analysis
        {"label": "Revenue Variance", "fieldname": "revenue_variance", "fieldtype": "Currency", "width": 120},
        {"label": "Cost Variance", "fieldname": "cost_variance", "fieldtype": "Currency", "width": 120},
        {"label": "Profit Variance", "fieldname": "profit_variance", "fieldtype": "Currency", "width": 120},
    ]


def format_date(date_str):
    """Format date string to dd-MMM-yy format."""
    if not date_str:
        return ""
    try:
        return formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str
