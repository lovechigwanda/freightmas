# Copyright (c) 2024, Lovech Technologies Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, date_diff
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
        {**standard_cols["customer"], "width": 180},
        standard_cols["reference"],
        
        # Port Information
        {"label": "Disch Port", "fieldname": "port_of_discharge", "fieldtype": "Link", "options": "Port", "width": 120},
        
        # Key Shipping Dates
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 100},
        {"label": "ATA", "fieldname": "ata", "fieldtype": "Data", "width": 100},
        
        # Status Information
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
        {"label": "Days", "fieldname": "days", "fieldtype": "Data", "width": 80},
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
    
    # Include both draft and submitted jobs for incoming cargo tracking
    job_filters["docstatus"] = ["in", [0, 1]]
    
    # Add customer reference filter if specified  
    if filters.get("customer_reference"):
        job_filters["customer_reference"] = ["like", f"%{filters['customer_reference']}%"]
    
    # Get data from database
    jobs = frappe.get_all(
        "Forwarding Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference", 
            "port_of_discharge", "eta", "ata", "discharge_date"
        ],
        order_by="date_created desc"
    )
    
    # Process data with incoming cargo logic
    data = []
    today = getdate()
    
    for job in jobs:
        eta = job.get("eta")
        ata = job.get("ata")
        discharge_date = job.get("discharge_date")
        
        # Skip jobs that are already discharged
        if discharge_date:
            continue
            
        status = ""
        days = ""
        
        if ata and not discharge_date:
            # Vessel arrived but cargo not discharged
            status = "Awaiting Discharge"
            days = "0"
        elif not ata:
            # Vessel not arrived yet
            if eta:
                eta_date = getdate(eta)
                days_diff = date_diff(eta_date, today)
                
                if days_diff > 0:
                    status = "En Route"
                    days = f"+{days_diff}"
                elif days_diff == 0:
                    status = "Due Today"
                    days = "0"
                else:
                    status = "Overdue Arrival"
                    days = str(days_diff)
            else:
                status = "No ETA"
                days = ""
        
        # Format data using standard utilities
        data.append({
            "name": job.get("name", ""),
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "port_of_discharge": job.get("port_of_discharge", ""),
            "eta": format_date(job.get("eta")),
            "ata": format_date(job.get("ata")),
            "status": status,
            "days": days,
        })
    
    return columns, data