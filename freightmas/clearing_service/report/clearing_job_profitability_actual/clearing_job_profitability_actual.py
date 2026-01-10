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

    conditions = ["1=1"]
    params = {}
    
    if filters.get("from_date"):
        conditions.append("date_created >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("date_created <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        params["customer"] = filters["customer"]
    if filters.get("bl_number"):
        conditions.append("bl_number LIKE %(bl_number)s")
        params["bl_number"] = "%" + filters["bl_number"] + "%"
    if filters.get("direction"):
        conditions.append("direction = %(direction)s")
        params["direction"] = filters["direction"]

    where_clause = " AND ".join(conditions)

    jobs = frappe.db.sql("""
        SELECT name, date_created, customer, direction, bl_number
        FROM `tabClearing Job`
        WHERE {where_clause}
        ORDER BY date_created DESC
    """.format(where_clause=where_clause), params, as_dict=True)

    for job in jobs:
        revenue = frappe.db.sql("""
            SELECT SUM(grand_total)
            FROM `tabSales Invoice`
            WHERE clearing_job_reference = %s AND docstatus = 1
        """, job.name)[0][0] or 0

        cost = frappe.db.sql("""
            SELECT SUM(grand_total)
            FROM `tabPurchase Invoice`
            WHERE clearing_job_reference = %s AND docstatus = 1
        """, job.name)[0][0] or 0

        profit = flt(revenue) - flt(cost)
        margin = (profit / revenue * 100) if revenue else 0

        data.append([
            job.name,
            job.date_created,
            job.customer,
            job.direction,
            job.bl_number,
            revenue,
            cost,
            profit,
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
