# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


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
    
    if filters.get("status"):
        conditions.append("status = %(status)s")
        params["status"] = filters["status"]

    where_clause = " AND ".join(conditions)

    jobs = frappe.db.sql("""
        SELECT name, date_created, customer, customer_reference, 
               direction, shipment_mode, port_of_loading, destination, 
               bl_number, eta, total_quoted_revenue_base, 
               total_quoted_cost_base, total_quoted_profit_base, status
        FROM `tabForwarding Job`
        WHERE {where_clause}
        ORDER BY date_created DESC
    """.format(where_clause=where_clause), params, as_dict=True)

    for job in jobs:
        # Combine direction and shipment mode
        direction_shipment = ""
        if job.get("direction") and job.get("shipment_mode"):
            direction_shipment = f"{job.get('shipment_mode')} {job.get('direction')}"
        elif job.get("direction"):
            direction_shipment = job.get("direction")
        elif job.get("shipment_mode"):
            direction_shipment = job.get("shipment_mode")

        data.append({
            "name": job.name,
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "direction": direction_shipment,
            "port_of_loading": job.get("port_of_loading", ""),
            "destination": job.get("destination", ""),
            "bl_number": job.get("bl_number", ""),
            "eta": format_date(job.get("eta")),
            "total_quoted_revenue_base": job.get("total_quoted_revenue_base", 0),
            "total_quoted_cost_base": job.get("total_quoted_cost_base", 0),
            "total_quoted_profit_base": job.get("total_quoted_profit_base", 0),
            "status": job.get("status", ""),
        })

    return columns, data


def get_columns():
    return [
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 140},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 120},
        {"label": "Origin", "fieldname": "port_of_loading", "fieldtype": "Link", "options": "Port", "width": 140},
        {"label": "Destination", "fieldname": "destination", "fieldtype": "Link", "options": "Port", "width": 140},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 140},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 100},
        {"label": "Est. Revenue", "fieldname": "total_quoted_revenue_base", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Cost", "fieldname": "total_quoted_cost_base", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Profit", "fieldname": "total_quoted_profit_base", "fieldtype": "Currency", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
    ]


def format_date(date_str):
    """Format date string to dd-MMM-yy format."""
    if not date_str:
        return ""
    try:
        return formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str
