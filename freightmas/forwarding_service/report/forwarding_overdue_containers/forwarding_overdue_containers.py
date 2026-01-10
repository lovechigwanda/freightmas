# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, date_diff, formatdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build conditions and parameters for parameterized query
    conditions = ["cpd.cargo_type = 'Containerised'", "cpd.parenttype = 'Forwarding Job'", "fj.docstatus IN (0, 1)"]
    params = {}
    
    if filters.get("from_date"):
        conditions.append("fj.date_created >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    
    if filters.get("to_date"):
        conditions.append("fj.date_created <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    
    if filters.get("customer"):
        conditions.append("fj.customer = %(customer)s")
        params["customer"] = filters["customer"]
    
    if filters.get("customer_reference"):
        conditions.append("fj.customer_reference LIKE %(customer_reference)s")
        params["customer_reference"] = "%" + filters["customer_reference"] + "%"

    where_clause = " AND ".join(conditions)

    # Get containerised cargo packages with job data using JOIN
    containers = frappe.db.sql("""
        SELECT cpd.parent, cpd.name, cpd.container_number, cpd.to_be_returned,
               cpd.load_by_date, cpd.return_by_date, cpd.is_loaded, 
               cpd.loaded_on_date, cpd.is_returned, cpd.returned_on_date,
               fj.date_created, fj.customer, fj.customer_reference
        FROM `tabCargo Parcel Details` cpd
        JOIN `tabForwarding Job` fj ON cpd.parent = fj.name
        WHERE {where_clause}
        ORDER BY fj.date_created DESC, cpd.name
    """.format(where_clause=where_clause), params, as_dict=True)

    # Process containers and filter for overdue ones
    today = getdate()
    
    for container in containers:
        loading_overdue = calculate_loading_overdue_days(container, today)
        return_overdue = calculate_return_overdue_days(container, today)
        
        # Only include containers that are actually overdue
        loading_days = loading_overdue if loading_overdue is not None else 0
        return_days = return_overdue if return_overdue is not None else 0
        
        if loading_days > 0 or return_days > 0:
            data.append({
                "name": container.get("parent"),
                "date_created": format_date(container.get("date_created")),
                "customer": container.get("customer", ""),
                "customer_reference": container.get("customer_reference", ""),
                "container_number": container.get("container_number", ""),
                "load_by_date": format_date(container.get("load_by_date")),
                "return_by_date": format_date(container.get("return_by_date")),
                "loading_overdue_days": loading_overdue,
                "return_overdue_days": return_overdue,
            })
    
    # Sort by most overdue first (loading overdue, then return overdue)
    data.sort(key=lambda x: (
        -(x["loading_overdue_days"] or 0),  # Most loading overdue first
        -(x["return_overdue_days"] or 0)   # Then most return overdue
    ))
    
    return columns, data

def get_columns():
    return [
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 140},
        {"label": "Container No", "fieldname": "container_number", "fieldtype": "Data", "width": 140},
        {"label": "Load By", "fieldname": "load_by_date", "fieldtype": "Data", "width": 100},
        {"label": "Return By", "fieldname": "return_by_date", "fieldtype": "Data", "width": 100},
        {"label": "Load O/D Days", "fieldname": "loading_overdue_days", "fieldtype": "Int", "width": 150},
        {"label": "Return O/D Days", "fieldname": "return_overdue_days", "fieldtype": "Int", "width": 150},
    ]

def calculate_loading_overdue_days(container, today):
    """Calculate loading overdue days - only for containers not yet loaded."""
    load_by = container.get("load_by_date")
    if not load_by or container.get("is_loaded"):
        return None
        
    load_by_date = getdate(load_by)
    overdue_days = date_diff(today, load_by_date)
    
    return overdue_days if overdue_days > 0 else None

def calculate_return_overdue_days(container, today):
    """Calculate return overdue days - only for containers that need to be returned but haven't been."""
    if not container.get("to_be_returned") or container.get("is_returned"):
        return None
        
    return_by = container.get("return_by_date")
    if not return_by:
        return None
        
    return_by_date = getdate(return_by)
    overdue_days = date_diff(today, return_by_date)
    
    return overdue_days if overdue_days > 0 else None

def format_date(date_str):
    """Format date string to dd-MMM-yy format."""
    if not date_str:
        return ""
    try:
        return formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str
