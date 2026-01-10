# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build conditions and parameters for parameterized query
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

    where_clause = " AND ".join(conditions)

    jobs = frappe.db.sql("""
        SELECT name, date_created, customer, customer_reference, direction, shipment_mode,
               port_of_loading, port_of_discharge, cargo_description, bl_number, status,
               total_quoted_revenue_base, total_quoted_cost_base,
               total_working_revenue_base, total_working_cost
        FROM `tabForwarding Job`
        WHERE {where_clause}
        ORDER BY date_created DESC
    """.format(where_clause=where_clause), params, as_dict=True)

    for job in jobs:
        # Quoted figures
        quoted_revenue = flt(job.total_quoted_revenue_base)
        quoted_cost = flt(job.total_quoted_cost_base)
        quoted_profit = quoted_revenue - quoted_cost

        # Working figures
        working_revenue = flt(job.total_working_revenue_base)
        working_cost = flt(job.total_working_cost)
        working_profit = working_revenue - working_cost

        # Draft invoices (docstatus = 0)
        draft_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE forwarding_job_reference = %s AND docstatus = 0
        """, job.name)[0][0] or 0

        draft_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE forwarding_job_reference = %s AND docstatus = 0
        """, job.name)[0][0] or 0

        draft_profit = flt(draft_revenue) - flt(draft_cost)

        # Actual invoices (docstatus = 1)
        actual_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE forwarding_job_reference = %s AND docstatus = 1
        """, job.name)[0][0] or 0

        actual_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE forwarding_job_reference = %s AND docstatus = 1
        """, job.name)[0][0] or 0

        actual_profit = flt(actual_revenue) - flt(actual_cost)

        # Build route display
        route = f"{job.port_of_loading or ''} → {job.port_of_discharge or ''}"
        
        # Build direction display
        direction_parts = []
        if job.shipment_mode:
            direction_parts.append(job.shipment_mode)
        if job.direction:
            direction_parts.append(job.direction)
        direction_display = " ".join(direction_parts)

        # Append raw values without currency formatting
        data.append({
            "name": job.name,
            "customer": job.customer,
            "reference": job.customer_reference,
            "direction": direction_display,
            "route": route,
            "cargo": job.cargo_description,
            "bl_number": job.bl_number,
            "status": job.status,
            "quoted_revenue": quoted_revenue,
            "quoted_cost": quoted_cost,
            "quoted_profit": quoted_profit,
            "working_revenue": working_revenue,
            "working_cost": working_cost,
            "working_profit": working_profit,
            "draft_revenue": draft_revenue,
            "draft_cost": draft_cost,
            "draft_profit": draft_profit,
            "actual_revenue": actual_revenue,
            "actual_cost": actual_cost,
            "actual_profit": actual_profit
        })

    return columns, data

def get_columns():
    return [
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": "Reference", "fieldname": "reference", "fieldtype": "Data", "width": 120},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 100},
        {"label": "Route", "fieldname": "route", "fieldtype": "Data", "width": 180},
        {"label": "Cargo", "fieldname": "cargo", "fieldtype": "Data", "width": 140},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Quoted Revenue", "fieldname": "quoted_revenue", "fieldtype": "Float", "width": 120},
        {"label": "Quoted Cost", "fieldname": "quoted_cost", "fieldtype": "Float", "width": 120},
        {"label": "Quoted Profit", "fieldname": "quoted_profit", "fieldtype": "Float", "width": 120},
        {"label": "Working Revenue", "fieldname": "working_revenue", "fieldtype": "Float", "width": 120},
        {"label": "Working Cost", "fieldname": "working_cost", "fieldtype": "Float", "width": 120},
        {"label": "Working Profit", "fieldname": "working_profit", "fieldtype": "Float", "width": 120},
        {"label": "Draft Revenue", "fieldname": "draft_revenue", "fieldtype": "Float", "width": 120},
        {"label": "Draft Cost", "fieldname": "draft_cost", "fieldtype": "Float", "width": 120},
        {"label": "Draft Profit", "fieldname": "draft_profit", "fieldtype": "Float", "width": 120},
        {"label": "Actual Revenue", "fieldname": "actual_revenue", "fieldtype": "Float", "width": 130},
        {"label": "Actual Cost", "fieldname": "actual_cost", "fieldtype": "Float", "width": 120},
        {"label": "Actual Profit", "fieldname": "actual_profit", "fieldtype": "Float", "width": 120}
    ]