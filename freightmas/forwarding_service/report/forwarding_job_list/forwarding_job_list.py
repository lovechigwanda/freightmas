# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
    
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build conditions for SQL query
    conditions = "1=1 AND docstatus IN (0, 1)"
    if filters.get("from_date"):
        conditions += f" AND date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND date_created <= '{filters['to_date']}'"
    if filters.get("customer"):
        conditions += f" AND customer = '{filters['customer']}'"
    if filters.get("status"):
        conditions += f" AND status = '{filters['status']}'"
    if filters.get("direction"):
        conditions += f" AND direction = '{filters['direction']}'"

    # Get forwarding jobs data - matching exact columns from screenshot
    jobs = frappe.db.sql(f"""
        SELECT name, date_created, customer, consignee, bl_number, 
               direction, status
        FROM `tabForwarding Job`
        WHERE {conditions}
        ORDER BY date_created DESC
    """, as_dict=True)

    for job in jobs:
        data.append({
            "id": job.name,
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "consignee": job.get("consignee", ""),
            "bl_number": job.get("bl_number", ""),
            "direction": job.get("direction", ""),
            "status": job.get("status", ""),
        })

    return columns, data


def get_columns():
    """Get column definitions matching the list view exactly."""
    return [
        {"label": "ID", "fieldname": "id", "fieldtype": "Link", "options": "Forwarding Job", "width": 150},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Data", "width": 130},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 210},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Link", "options": "Customer", "width": 210},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 160},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 130},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 130},
    ]


def format_date(date_str):
    """Format date string to dd-MMM-yy format."""
    if date_str:
        try:
            return formatdate(date_str, "dd-MMM-yy")
        except:
            return str(date_str)
    return ""