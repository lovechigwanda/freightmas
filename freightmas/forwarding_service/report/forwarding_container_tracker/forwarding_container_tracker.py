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
    
    if filters.get("container_number"):
        conditions.append("cpd.container_number LIKE %(container_number)s")
        params["container_number"] = "%" + filters["container_number"] + "%"

    where_clause = " AND ".join(conditions)

    # Get containerised cargo packages with job data using JOIN with parameterized query
    containers = frappe.db.sql("""
        SELECT cpd.parent, cpd.name, cpd.container_number, cpd.container_type, cpd.to_be_returned,
               cpd.load_by_date, cpd.return_by_date, cpd.is_booked, cpd.booked_on_date,
               cpd.is_loaded, cpd.loaded_on_date, cpd.is_offloaded, cpd.offloaded_on_date,
               cpd.is_returned, cpd.returned_on_date, cpd.is_completed, cpd.completed_on_date,
               cpd.truck_reg_no, cpd.trailer_reg_no, cpd.driver_name,
               fj.date_created, fj.customer, fj.customer_reference, fj.direction, fj.shipment_mode
        FROM `tabCargo Parcel Details` cpd
        JOIN `tabForwarding Job` fj ON cpd.parent = fj.name
        WHERE {where_clause}
        ORDER BY fj.date_created DESC, cpd.name
    """.format(where_clause=where_clause), params, as_dict=True)

    # Process containers and add calculated fields
    for container in containers:
        # Calculate container status and overdue days
        container_status = calculate_container_status(container)
        loading_overdue = calculate_loading_overdue_days(container)
        return_overdue = calculate_return_overdue_days(container)
        
        # Combine direction and shipment mode
        direction = container.get("direction", "")
        shipment_mode = container.get("shipment_mode", "")
        combined_direction = f"{shipment_mode} {direction}" if shipment_mode and direction else (shipment_mode or direction or "")
        
        data.append({
            "name": container.get("parent"),
            "customer": container.get("customer", ""),
            "customer_reference": container.get("customer_reference", ""),
            "container_number": container.get("container_number", ""),
            "container_type": container.get("container_type", ""),
            "container_status": container_status,
            "load_by_date": format_date(container.get("load_by_date")),
            "return_by_date": format_date(container.get("return_by_date")),
            "loading_overdue_days": loading_overdue,
        })
    
    return columns, data

def get_columns():
    return [
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 190},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 160},
        {"label": "Container No", "fieldname": "container_number", "fieldtype": "Data", "width": 150},
        {"label": "Type", "fieldname": "container_type", "fieldtype": "Link", "options": "Container Type", "width": 120},
        {"label": "Status", "fieldname": "container_status", "fieldtype": "Data", "width": 140},
        {"label": "Load By", "fieldname": "load_by_date", "fieldtype": "Data", "width": 100},
        {"label": "Return By", "fieldname": "return_by_date", "fieldtype": "Data", "width": 100},
        {"label": "O/D Days", "fieldname": "loading_overdue_days", "fieldtype": "Int", "width": 100},
    ]

def calculate_container_status(container):
    """Calculate container status based on milestone tracking."""
    if container.get("is_completed"):
        return "Completed"
    elif container.get("is_returned"):
        return "Returned"
    elif container.get("is_offloaded"):
        return "Offloaded"
    elif container.get("is_loaded"):
        return "Loaded"
    elif container.get("is_booked"):
        return "Booked"
    else:
        return "Pending Booking"

def calculate_loading_overdue_days(container):
    """Calculate loading overdue days."""
    load_by = container.get("load_by_date")
    if not load_by:
        return None
        
    # Use loaded_on_date if container is loaded, otherwise use today
    if container.get("is_loaded") and container.get("loaded_on_date"):
        comparison_date = getdate(container.get("loaded_on_date"))
    else:
        comparison_date = getdate()
    
    load_by_date = getdate(load_by)
    overdue_days = date_diff(comparison_date, load_by_date)
    
    # Return None if already loaded (calc ends when loaded)
    if container.get("is_loaded"):
        return overdue_days if overdue_days > 0 else None
        
    # Return overdue days (positive means overdue)
    return overdue_days if overdue_days > 0 else None

def calculate_return_overdue_days(container):
    """Calculate return overdue days."""
    # If container doesn't need to be returned, return None
    if not container.get("to_be_returned"):
        return None
        
    return_by = container.get("return_by_date")
    if not return_by:
        return None
        
    # Use returned_on_date if container is returned, otherwise use today
    if container.get("is_returned") and container.get("returned_on_date"):
        comparison_date = getdate(container.get("returned_on_date"))
    else:
        comparison_date = getdate()
    
    return_by_date = getdate(return_by)
    overdue_days = date_diff(comparison_date, return_by_date)
    
    # Return None if already returned (calc ends when returned)
    if container.get("is_returned"):
        return overdue_days if overdue_days > 0 else None
        
    # Return overdue days (positive means overdue)
    return overdue_days if overdue_days > 0 else None

def format_checkbox(value):
    """Format checkbox value for display."""
    return "Yes" if value else "No"

def format_date(date_str):
    """Format date string to dd-MMM-yy format."""
    if not date_str:
        return ""
    try:
        return formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str