# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from freightmas.utils.report_utils import (
    format_date,
    get_standard_columns,
    build_job_filters,
    combine_direction_shipment,
    validate_date_filters
)

def get_columns():
    standard_cols = get_standard_columns()
    columns = [
        {**standard_cols["job_id"], "options": "Forwarding Job"},
        standard_cols["job_date"],
        standard_cols["customer"],
        standard_cols["reference"],
        standard_cols["direction"],
        standard_cols["status"],
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
    return columns

def execute(filters=None):
    filters = validate_date_filters(filters or {})
    columns = get_columns()
    job_filters = build_job_filters(filters, "Forwarding Job")
    job_filters["docstatus"] = ["in", [0, 1]]
    jobs = frappe.get_all(
        "Forwarding Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference", "direction", "status",
            "total_quoted_revenue_base", "total_quoted_cost_base", "total_quoted_profit_base", "quoted_margin_percent",
            "total_working_revenue_base", "total_working_cost", "total_working_profit_base", "profit_margin_percent"
        ],
        order_by="date_created desc"
    )
    data = []
    for job in jobs:
        # Quoted
        quoted_revenue = job.get("total_quoted_revenue_base", 0)
        quoted_cost = job.get("total_quoted_cost_base", 0)
        quoted_profit = job.get("total_quoted_profit_base", 0)
        quoted_margin = job.get("quoted_margin_percent", 0)
        # Working
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
            "date_created": format_date(job["date_created"]),
            "customer": job["customer"],
            "customer_reference": job["customer_reference"],
            "direction": job["direction"],
            "status": job["status"],
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
