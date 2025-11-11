# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from freightmas.utils.report_utils import (
    format_date,
    format_checkbox,
    get_standard_columns,
    build_job_filters,
    combine_direction_shipment,
    validate_date_filters
)

def get_columns():
    """Get extended column definitions using standard utilities where possible."""
    standard_cols = get_standard_columns()
    
    # Use standard columns where possible, define custom ones for extended fields
    columns = [
        # Standard columns with customizations
        {**standard_cols["job_id"], "options": "Forwarding Job"},
        standard_cols["job_date"],
        standard_cols["customer"],
        standard_cols["reference"],
        standard_cols["direction"],
        
        # Custom extended columns
        {"label": "Type", "fieldname": "shipment_type", "fieldtype": "Data", "width": 60},
        standard_cols["cargo_description"],
        standard_cols["shipper"],
        standard_cols["consignee"],
        standard_cols["origin"],
        {"label": "Disch Port", "fieldname": "port_of_discharge", "fieldtype": "Link", "options": "Port", "width": 120},
        standard_cols["destination"],
        standard_cols["bl_number"],
        {"label": "BL Type", "fieldname": "bl_type", "fieldtype": "Data", "width": 80},
        {"label": "Vess/Flt", "fieldname": "vessel_flight_no", "fieldtype": "Data", "width": 100},
        {"label": "Bkng Date", "fieldname": "booking_date", "fieldtype": "Data", "width": 110},
        {"label": "Cargo Ready", "fieldname": "cargo_ready_date", "fieldtype": "Data", "width": 110},
        standard_cols["etd"],
        standard_cols["eta"],
        standard_cols["atd"],
        standard_cols["ata"],
        {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "Data", "width": 110},
        {"label": "BL Recvd", "fieldname": "is_bl_received", "fieldtype": "Data", "width": 80},
        {"label": "BL Confmd", "fieldname": "is_bl_confirmed", "fieldtype": "Data", "width": 80},
        {"label": "Incoterms", "fieldname": "incoterms", "fieldtype": "Link", "options": "Incoterm", "width": 80},
        standard_cols["estimated_revenue"],
        standard_cols["estimated_cost"],
        standard_cols["estimated_profit"],
        standard_cols["status"],
        standard_cols["completed_on"],
    ]
    
    return columns

def execute(filters=None):
    """
    Main execution function using standardized utilities.
    """
    # Validate and normalize filters
    filters = validate_date_filters(filters or {})
    
    # Get columns using utilities
    columns = get_columns()
    
    # Build database filters using utilities
    job_filters = build_job_filters(filters, "Forwarding Job")
    
    # Get extended data from database
    jobs = frappe.get_all(
        "Forwarding Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference", 
            "direction", "shipment_mode", "shipment_type", "cargo_description", 
            "shipper", "consignee", "port_of_loading", "port_of_discharge", 
            "destination", "bl_number", "bl_type", "vessel_flight_no", 
            "booking_date", "cargo_ready_date", "etd", "eta", "atd", "ata", 
            "delivery_date", "is_bl_received", "is_bl_confirmed", "incoterms",
            "total_quoted_revenue_base", "total_quoted_cost_base", 
            "total_quoted_profit_base", "status", "completed_on"
        ],
        order_by="date_created desc"
    )
    
    # Process extended data with consistent formatting
    data = []
    for job in jobs:
        data.append({
            "name": job.get("name", ""),
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "direction": combine_direction_shipment(job),
            "shipment_type": job.get("shipment_type", ""),
            "cargo_description": job.get("cargo_description", ""),
            "shipper": job.get("shipper", ""),
            "consignee": job.get("consignee", ""),
            "port_of_loading": job.get("port_of_loading", ""),
            "port_of_discharge": job.get("port_of_discharge", ""),
            "destination": job.get("destination", ""),
            "bl_number": job.get("bl_number", ""),
            "bl_type": job.get("bl_type", ""),
            "vessel_flight_no": job.get("vessel_flight_no", ""),
            "booking_date": format_date(job.get("booking_date")),
            "cargo_ready_date": format_date(job.get("cargo_ready_date")),
            "etd": format_date(job.get("etd")),
            "eta": format_date(job.get("eta")),
            "atd": format_date(job.get("atd")),
            "ata": format_date(job.get("ata")),
            "delivery_date": format_date(job.get("delivery_date")),
            "is_bl_received": format_checkbox(job.get("is_bl_received", 0)),
            "is_bl_confirmed": format_checkbox(job.get("is_bl_confirmed", 0)),
            "incoterms": job.get("incoterms", ""),
            "total_quoted_revenue_base": job.get("total_quoted_revenue_base", 0),
            "total_quoted_cost_base": job.get("total_quoted_cost_base", 0),
            "total_quoted_profit_base": job.get("total_quoted_profit_base", 0),
            "status": job.get("status", ""),
            "completed_on": format_date(job.get("completed_on", "")),
        })
    
    return columns, data
