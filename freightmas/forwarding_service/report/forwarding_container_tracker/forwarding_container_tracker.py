# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, date_diff
from freightmas.utils.report_utils import (
    format_date,
    format_checkbox,
    get_standard_columns,
    build_job_filters,
    validate_date_filters
)

def get_columns():
    """Get column definitions for Forwarding Container Tracker using standard utilities."""
    standard_cols = get_standard_columns()
    
    columns = [
        # Core Job Information
        {**standard_cols["job_id"], "options": "Forwarding Job"},
        standard_cols["job_date"],
        standard_cols["customer"],
        standard_cols["reference"],
        
        # Container Details
        {"label": "Container No", "fieldname": "container_number", "fieldtype": "Data", "width": 140},
        {"label": "Container Type", "fieldname": "container_type", "fieldtype": "Link", "options": "Container Type", "width": 120},
        {"label": "Load By", "fieldname": "load_by_date", "fieldtype": "Data", "width": 100},
        
        # Container Status & Tracking
        {"label": "To Return", "fieldname": "to_be_returned", "fieldtype": "Data", "width": 80},
        {"label": "Return By", "fieldname": "return_by_date", "fieldtype": "Data", "width": 100},
        {"label": "Container Status", "fieldname": "container_status", "fieldtype": "Data", "width": 140},
        
        # Transport Details (moved after container status)
        {"label": "Truck Reg No", "fieldname": "truck_reg_no", "fieldtype": "Data", "width": 120, "align": "left"},
        {"label": "Trailer Reg No", "fieldname": "trailer_reg_no", "fieldtype": "Data", "width": 120, "align": "left"},
        {"label": "Driver Name", "fieldname": "driver_name", "fieldtype": "Data", "width": 140, "align": "left"},
        
        # Dates Tracking
        {"label": "Loaded On", "fieldname": "loaded_on_date", "fieldtype": "Data", "width": 100},
        {"label": "Offloaded On", "fieldname": "offloaded_on_date", "fieldtype": "Data", "width": 100},
        {"label": "Returned On", "fieldname": "returned_on_date", "fieldtype": "Data", "width": 100},
        {"label": "Completed On", "fieldname": "completed_on_date", "fieldtype": "Data", "width": 100},
        
        # Calculated Fields
        {"label": "Loading Overdue Days", "fieldname": "loading_overdue_days", "fieldtype": "Int", "width": 150},
        {"label": "Return Overdue Days", "fieldname": "return_overdue_days", "fieldtype": "Int", "width": 150},
    ]
    
    return columns

def calculate_container_status(container):
    """
    Calculate container status based on milestone tracking.
    
    Args:
        container: Dictionary with container data
        
    Returns:
        String status description
    """
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
    """
    Calculate loading overdue days.
    
    Logic: Today or Loaded On Date minus Load By Date
    Calc ends when container has loaded.
    
    Args:
        container: Dictionary with container data
        
    Returns:
        Integer days overdue (negative means early, 0 means on time)
    """
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
    """
    Calculate return overdue days.
    
    Logic: Today or Returned On Date minus Return By Date
    Calc ends when container has been returned.
    If container is not to be returned, show blank.
    
    Args:
        container: Dictionary with container data
        
    Returns:
        Integer days overdue or None
    """
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

def execute(filters=None):
    """
    Main execution function for Forwarding Container Tracker report.
    """
    # Validate and normalize filters
    filters = validate_date_filters(filters or {})
    
    # Get columns
    columns = get_columns()
    
    # Build database filters for Forwarding Jobs
    job_filters = build_job_filters(filters, "Forwarding Job")
    
    # Get containerised cargo packages first to identify relevant jobs
    container_filters = {
        "cargo_type": "Containerised",
        "parenttype": "Forwarding Job"
    }
    
    # Add container-specific filters
    if filters.get("container_number"):
        container_filters["container_number"] = ["like", f"%{filters['container_number']}%"]
    
    # Get containerised cargo packages
    containers = frappe.get_all(
        "Cargo Parcel Details",
        filters=container_filters,
        fields=[
            "parent", "name", "container_number", "container_type", "to_be_returned",
            "load_by_date", "return_by_date", "is_booked", "booked_on_date",
            "is_loaded", "loaded_on_date", "is_offloaded", "offloaded_on_date",
            "is_returned", "returned_on_date", "is_completed", "completed_on_date",
            "truck_reg_no", "trailer_reg_no", "driver_name"
        ],
        order_by="parent desc, name"
    )
    
    if not containers:
        return columns, []
    
    # Get unique job names from containers
    job_names = list(set([container["parent"] for container in containers]))
    
    # Add job filter for containerised jobs only
    if job_names:
        job_filters["name"] = ["in", job_names]
    else:
        return columns, []
    
    # Get forwarding job data
    jobs = frappe.get_all(
        "Forwarding Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference", 
            "direction", "shipment_mode"
        ],
        order_by="date_created desc"
    )
    
    # Create a job lookup dictionary
    job_lookup = {job["name"]: job for job in jobs}
    
    # Process data
    data = []
    for container in containers:
        job_name = container.get("parent")
        job_data = job_lookup.get(job_name)
        
        if not job_data:
            continue
            
        # Calculate container status and overdue days
        container_status = calculate_container_status(container)
        loading_overdue = calculate_loading_overdue_days(container)
        return_overdue = calculate_return_overdue_days(container)
        
        # Combine direction and shipment mode
        direction = job_data.get("direction", "")
        shipment_mode = job_data.get("shipment_mode", "")
        combined_direction = f"{shipment_mode} {direction}" if shipment_mode and direction else (shipment_mode or direction or "")
        
        row = {
            # Core Job Information
            "name": job_name,
            "date_created": format_date(job_data.get("date_created")),
            "customer": job_data.get("customer", ""),
            "customer_reference": job_data.get("customer_reference", ""),
            "direction": combined_direction,
            
            # Container Details
            "container_number": container.get("container_number", ""),
            "container_type": container.get("container_type", ""),
            "load_by_date": format_date(container.get("load_by_date")),
            
            # Container Status & Tracking
            "to_be_returned": format_checkbox(container.get("to_be_returned", 0)),
            "return_by_date": format_date(container.get("return_by_date")),
            "container_status": container_status,
            
            # Dates Tracking
            "loaded_on_date": format_date(container.get("loaded_on_date")),
            "offloaded_on_date": format_date(container.get("offloaded_on_date")),
            "returned_on_date": format_date(container.get("returned_on_date")),
            "completed_on_date": format_date(container.get("completed_on_date")),
            
            # Transport Details
            "truck_reg_no": container.get("truck_reg_no", ""),
            "trailer_reg_no": container.get("trailer_reg_no", ""),
            "driver_name": container.get("driver_name", ""),
            
            # Calculated Fields
            "loading_overdue_days": loading_overdue,
            "return_overdue_days": return_overdue,
        }
        
        data.append(row)
    
    return columns, data