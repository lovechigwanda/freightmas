# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    conditions = "1=1"
    if filters.get("from_date"):
        conditions += f" AND date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND date_created <= '{filters['to_date']}'"
    if filters.get("customer"):
        conditions += f" AND customer = '{filters['customer']}'"
    if filters.get("bl_number"):
        conditions += f" AND bl_number LIKE '%{filters['bl_number']}%'"
    if filters.get("direction"):
        conditions += f" AND direction = '{filters['direction']}'"

    jobs = frappe.db.sql(f"""
        SELECT name, date_created, customer, direction, bl_number,
               total_estimated_revenue, total_estimated_cost
        FROM `tabClearing Job`
        WHERE {conditions}
        ORDER BY date_created DESC
    """, as_dict=True)

    for job in jobs:
        est_revenue = flt(job.total_estimated_revenue)
        est_cost = flt(job.total_estimated_cost)
        est_profit = est_revenue - est_cost

        # Draft Sales Invoices
        draft_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE clearing_job_reference = %s AND docstatus = 0
        """, job.name)[0][0] or 0

        # Draft Purchase Invoices
        draft_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE clearing_job_reference = %s AND docstatus = 0
        """, job.name)[0][0] or 0

        draft_profit = flt(draft_revenue) - flt(draft_cost)

        # Submitted Sales Invoices
        actual_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE clearing_job_reference = %s AND docstatus = 1
        """, job.name)[0][0] or 0

        # Submitted Purchase Invoices
        actual_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE clearing_job_reference = %s AND docstatus = 1
        """, job.name)[0][0] or 0

        actual_profit = flt(actual_revenue) - flt(actual_cost)

        data.append([
            job.name,
            job.customer,
            job.direction,
            job.bl_number,
            est_revenue,
            est_cost,
            est_profit,
            draft_revenue,
            draft_cost,
            draft_profit,
            actual_revenue,
            actual_cost,
            actual_profit
        ])

    return columns, data

def get_columns():
    return [
        {"label": "Job No", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 100},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 140},
        {"label": "Est. Revenue", "fieldname": "est_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Cost", "fieldname": "est_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Profit", "fieldname": "est_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Draft Revenue", "fieldname": "draft_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Draft Cost", "fieldname": "draft_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Draft Profit", "fieldname": "draft_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Actual Revenue", "fieldname": "actual_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Actual Cost", "fieldname": "actual_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Actual Profit", "fieldname": "actual_profit", "fieldtype": "Currency", "width": 120},
    ]
