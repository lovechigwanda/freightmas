# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, date_diff
from freightmas.utils.report_utils import (
    format_date,
    get_standard_columns,
    build_job_filters,
    validate_date_filters
)

def get_columns():
    """Get simplified column definitions for Forwarding Overdue Containers."""
    standard_cols = get_standard_columns()
    
    columns = [
        # Core Job Information
        {**standard_cols["job_id"], "options": "Forwarding Job"},
        standard_cols["job_date"],
        standard_cols["customer"],
        standard_cols["reference"],
        
        # Container Details
        {"label": "Container No", "fieldname": "container_number", "fieldtype": "Data", "width": 140},
        {"label": "Load By", "fieldname": "load_by_date", "fieldtype": "Data", "width": 100},
        {"label": "Return By", "fieldname": "return_by_date", "fieldtype": "Data", "width": 100},
        
        # Overdue Calculations
        {"label": "Loading Overdue Days", "fieldname": "loading_overdue_days", "fieldtype": "Int", "width": 150},
        {"label": "Return Overdue Days", "fieldname": "return_overdue_days", "fieldtype": "Int", "width": 150},
    ]
    
    return columns

def calculate_loading_overdue_days(container):
    """
    Calculate loading overdue days.
    
    Logic: Today or Loaded On Date minus Load By Date
    Only return positive values (overdue), and only if not yet loaded.
    
    Args:
        container: Dictionary with container data
        
    Returns:
        Integer days overdue (only positive values) or None
    """
    load_by = container.get("load_by_date")
    if not load_by:
        return None
        
    # If already loaded, no overdue calculation needed for this report
    if container.get("is_loaded"):
        return None
        
    # Use today since not yet loaded
    today = getdate()
    load_by_date = getdate(load_by)
    overdue_days = date_diff(today, load_by_date)
    
    # Return only positive (overdue) days
    return overdue_days if overdue_days > 0 else None

def calculate_return_overdue_days(container):
    """
    Calculate return overdue days.
    
    Logic: Today or Returned On Date minus Return By Date
    Only return positive values (overdue), and only if not yet returned.
    If container doesn't need to be returned, return None.
    
    Args:
        container: Dictionary with container data
        
    Returns:
        Integer days overdue (only positive values) or None
    """
    # If container doesn't need to be returned, no overdue calculation
    if not container.get("to_be_returned"):
        return None
        
    return_by = container.get("return_by_date")
    if not return_by:
        return None
        
    # If already returned, no overdue calculation needed for this report
    if container.get("is_returned"):
        return None
        
    # Use today since not yet returned
    today = getdate()
    return_by_date = getdate(return_by)
    overdue_days = date_diff(today, return_by_date)
    
    # Return only positive (overdue) days
    return overdue_days if overdue_days > 0 else None

def execute(filters=None):
    """
    Main execution function for Forwarding Overdue Containers report.
    Only returns containers that are overdue for loading or return.
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
    
    # Get containerised cargo packages
    containers = frappe.get_all(
        "Cargo Parcel Details",
        filters=container_filters,
        fields=[
            "parent", "name", "container_number", "to_be_returned",
            "load_by_date", "return_by_date",
            "is_loaded", "loaded_on_date", 
            "is_returned", "returned_on_date"
        ],
        order_by="parent desc, name"
    )
    
    if not containers:
        return columns, []
    
    # Filter for only overdue containers
    overdue_containers = []
    for container in containers:
        loading_overdue = calculate_loading_overdue_days(container)
        return_overdue = calculate_return_overdue_days(container)
        
        # Convert None to 0 for calculation
        loading_days = loading_overdue if loading_overdue is not None else 0
        return_days = return_overdue if return_overdue is not None else 0
        
        # Include only if there are actual overdue days (sum > 0)
        if loading_days > 0 or return_days > 0:
            container["loading_overdue_days"] = loading_overdue  # Keep original None/value
            container["return_overdue_days"] = return_overdue    # Keep original None/value
            overdue_containers.append(container)
    
    if not overdue_containers:
        return columns, []
    
    # Get unique job names from overdue containers
    job_names = list(set([container["parent"] for container in overdue_containers]))
    
    # Add job filter for overdue container jobs only
    if job_names:
        job_filters["name"] = ["in", job_names]
    else:
        return columns, []
    
    # Get forwarding job data
    jobs = frappe.get_all(
        "Forwarding Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference"
        ],
        order_by="date_created desc"
    )
    
    # Create a job lookup dictionary
    job_lookup = {job["name"]: job for job in jobs}
    
    # Process data
    data = []
    for container in overdue_containers:
        job_name = container.get("parent")
        job_data = job_lookup.get(job_name)
        
        if not job_data:
            continue
            
        row = {
            # Core Job Information (fieldnames must match column definitions)
            "name": job_name,  # This maps to "Job ID" column
            "date_created": format_date(job_data.get("date_created")),  # This maps to "Job Date" column
            "customer": job_data.get("customer", ""),
            "customer_reference": job_data.get("customer_reference", ""),
            
            # Container Details
            "container_number": container.get("container_number", ""),
            
            # Key Dates (only due dates, not actual dates since they'll be empty)
            "load_by_date": format_date(container.get("load_by_date")),
            "return_by_date": format_date(container.get("return_by_date")),
            
            # Overdue Days
            "loading_overdue_days": container.get("loading_overdue_days"),
            "return_overdue_days": container.get("return_overdue_days"),
        }
        
        # Double-check: Only add rows that actually have overdue days > 0
        loading_days = row["loading_overdue_days"] if row["loading_overdue_days"] is not None else 0
        return_days = row["return_overdue_days"] if row["return_overdue_days"] is not None else 0
        
        # Only include if there are actual overdue days
        if loading_days > 0 or return_days > 0:
            data.append(row)
    
    # Sort by most overdue first (loading overdue, then return overdue)
    data.sort(key=lambda x: (
        -(x["loading_overdue_days"] or 0),  # Most loading overdue first
        -(x["return_overdue_days"] or 0)   # Then most return overdue
    ))
    
    return columns, data
