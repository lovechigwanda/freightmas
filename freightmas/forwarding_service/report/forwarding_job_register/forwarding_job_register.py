# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from freightmas.utils.report_utils import (
    format_date,
    get_standard_columns,
    build_job_filters,
    combine_direction_shipment,
    validate_date_filters
)

def get_columns():
    """Get column definitions using standard utilities."""
    standard_cols = get_standard_columns()
    
    # Use standard columns where possible, customize as needed
    columns = [
        # Update the job_id column to link to Forwarding Job
        {**standard_cols["job_id"], "options": "Forwarding Job"},
        standard_cols["job_date"],
        {**standard_cols["customer"], "width": 200},  # Slightly wider for customer names
        standard_cols["reference"],
        standard_cols["direction"],
        standard_cols["origin"],
        standard_cols["destination"],
        standard_cols["bl_number"],
        {**standard_cols["eta"], "width": 100},  # Wider for date format
        standard_cols["estimated_revenue"],
        standard_cols["estimated_cost"],
        standard_cols["estimated_profit"],
        standard_cols["status"],
    ]
    
    return columns

def execute(filters=None):
    """
    Main execution function using standardized utilities.
    """
    # Validate and normalize filters
    filters = validate_date_filters(filters or {})
    
    # Get columns using standard utilities
    columns = get_columns()
    
    # Build database filters using utilities
    job_filters = build_job_filters(filters, "Forwarding Job")
    
    # Get data from database
    jobs = frappe.get_all(
        "Forwarding Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference", 
            "direction", "shipment_mode", "port_of_loading", "destination", 
            "bl_number", "eta", "total_quoted_revenue_base", 
            "total_quoted_cost_base", "total_quoted_profit_base", "status"
        ],
        order_by="date_created desc"
    )
    
    # Process data with consistent formatting
    data = []
    for job in jobs:
        data.append({
            "name": job.get("name", ""),
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "direction": combine_direction_shipment(job),
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
