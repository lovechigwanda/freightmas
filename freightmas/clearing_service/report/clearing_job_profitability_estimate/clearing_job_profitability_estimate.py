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
               total_estimated_revenue AS revenue,
               total_estimated_cost AS cost,
               total_estimated_profit AS profit
        FROM `tabClearing Job`
        WHERE {conditions}
        ORDER BY date_created DESC
    """, as_dict=True)

    for job in jobs:
        margin = 0
        if job.revenue:
            margin = (flt(job.profit) / flt(job.revenue)) * 100

        data.append([
            job.name,
            job.date_created,
            job.customer,
            job.direction,
            job.bl_number,
            job.revenue,
            job.cost,
            job.profit,
            margin
        ])

    return columns, data

def get_columns():
    return [
        {"label": "Job No", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Date", "width": 110},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 100},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 140},
        {"label": "Revenue", "fieldname": "revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Cost", "fieldname": "cost", "fieldtype": "Currency", "width": 120},
        {"label": "Profit", "fieldname": "profit", "fieldtype": "Currency", "width": 120},
        {"label": "Profit Margin (%)", "fieldname": "profit_margin", "fieldtype": "Percent", "width": 120},
    ]
