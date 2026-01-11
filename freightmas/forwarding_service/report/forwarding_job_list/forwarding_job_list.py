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
    conditions = ["docstatus IN (0, 1)"]
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
    
    if filters.get("direction"):
        conditions.append("direction = %(direction)s")
        params["direction"] = filters["direction"]

    where_clause = " AND ".join(conditions)

    # Handle pagination
    limit_clause = ""
    if filters.get("page_length") and filters.get("page_length") != "All":
        page_length = int(filters.get("page_length", 20))
        start = int(filters.get("start", 0))
        limit_clause = f" LIMIT {page_length} OFFSET {start}"

    # Get forwarding jobs data - matching exact columns from screenshot
    jobs = frappe.db.sql("""
        SELECT name, date_created, customer, consignee, customer_reference, 
               eta, direction, status
        FROM `tabForwarding Job`
        WHERE {where_clause}
        ORDER BY date_created DESC
        {limit_clause}
    """.format(where_clause=where_clause, limit_clause=limit_clause), params, as_dict=True)

    for job in jobs:
        data.append({
            "id": job.name,
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "consignee": job.get("consignee", ""),
            "customer_reference": job.get("customer_reference", ""),
            "eta": format_date(job.get("eta")),
            "direction": job.get("direction", ""),
            "status": job.get("status", ""),
        })

    # Return data for pagination
    result = {"data": data, "columns": columns}
    
    # Add total count for pagination if limit is applied
    if limit_clause:
        total_count = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabForwarding Job`
            WHERE {where_clause}
        """.format(where_clause=where_clause), params, as_dict=True)[0].count
        result["total"] = total_count
    
    return columns, data


def get_columns():
    """Get column definitions matching the list view exactly."""
    return [
        {"label": "ID", "fieldname": "id", "fieldtype": "Link", "options": "Forwarding Job", "width": 150},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Data", "width": 130},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 210},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Data", "width": 210},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 160},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 110},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 110},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
    ]


def format_date(date_str):
    """Format date string to dd-MMM-yy format."""
    if date_str:
        try:
            return formatdate(date_str, "dd-MMM-yy")
        except:
            return str(date_str)
    return ""