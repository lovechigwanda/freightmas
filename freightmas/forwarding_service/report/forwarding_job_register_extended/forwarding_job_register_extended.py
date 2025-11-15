# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import formatdate

def get_columns():
    """Get comprehensive column definitions with additional important fields and charges analysis."""
    columns = [
        # Core Job Information
        {"label": "Job ID", "fieldname": "job_id", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 140},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
        
        # Shipment Details
        {"label": "Mode", "fieldname": "shipment_mode", "fieldtype": "Data", "width": 60},
        {"label": "Type", "fieldname": "shipment_type", "fieldtype": "Data", "width": 60},
        {"label": "Cargo Description", "fieldname": "cargo_description", "fieldtype": "Data", "width": 180},
        {"label": "Cargo Count", "fieldname": "cargo_count", "fieldtype": "Data", "width": 100},
        
        # Parties
        {"label": "Shipper", "fieldname": "shipper", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Notify Party", "fieldname": "notify_party", "fieldtype": "Link", "options": "Customer", "width": 120},
        
        # Routing Information
        {"label": "Origin", "fieldname": "port_of_loading", "fieldtype": "Link", "options": "Port", "width": 110},
        {"label": "Discharge", "fieldname": "port_of_discharge", "fieldtype": "Link", "options": "Port", "width": 110},
        {"label": "Destination", "fieldname": "destination", "fieldtype": "Link", "options": "Port", "width": 110},
        {"label": "Origin Country", "fieldname": "origin_country", "fieldtype": "Data", "width": 100},
        {"label": "Dest Country", "fieldname": "destination_country", "fieldtype": "Data", "width": 100},
        
        # Transport Details
        {"label": "Vessel/Flight", "fieldname": "vessel_flight_no", "fieldtype": "Data", "width": 120},
        {"label": "Vessel Date", "fieldname": "vessel_flight_date", "fieldtype": "Data", "width": 100},
        
        # Important Dates
        {"label": "Booking Date", "fieldname": "booking_date", "fieldtype": "Data", "width": 100},
        {"label": "Cargo Ready", "fieldname": "cargo_ready_date", "fieldtype": "Data", "width": 100},
        {"label": "ETD", "fieldname": "etd", "fieldtype": "Data", "width": 85},
        {"label": "ATD", "fieldname": "atd", "fieldtype": "Data", "width": 85},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 85},
        {"label": "ATA", "fieldname": "ata", "fieldtype": "Data", "width": 85},
        {"label": "Discharge Date", "fieldname": "discharge_date", "fieldtype": "Data", "width": 100},
        {"label": "Completed On", "fieldname": "completed_on", "fieldtype": "Data", "width": 100},
        
        # Bill of Lading Information
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 140},
        {"label": "BL Type", "fieldname": "bl_type", "fieldtype": "Data", "width": 80},
        {"label": "BL Issued", "fieldname": "bl_issued_date", "fieldtype": "Data", "width": 85},
        {"label": "BL Recvd", "fieldname": "is_bl_received", "fieldtype": "Data", "width": 80},
        {"label": "BL Recvd Date", "fieldname": "bl_received_date", "fieldtype": "Data", "width": 95},
        {"label": "BL Confmd", "fieldname": "is_bl_confirmed", "fieldtype": "Data", "width": 80},
        {"label": "BL Confmd Date", "fieldname": "bl_confirmed_date", "fieldtype": "Data", "width": 95},
        
        # Trade Terms
        {"label": "Incoterms", "fieldname": "incoterms", "fieldtype": "Link", "options": "Incoterm", "width": 80},
        {"label": "Incoterm Place", "fieldname": "incoterm_place", "fieldtype": "Data", "width": 120},
        
        # Currency Information
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
        {"label": "Exchange Rate", "fieldname": "conversion_rate", "fieldtype": "Float", "width": 100},
        
        # Trucking Information
        {"label": "Trucking Req", "fieldname": "is_trucking_required", "fieldtype": "Data", "width": 90},
        {"label": "Trucks Required", "fieldname": "trucks_required", "fieldtype": "Data", "width": 100},
        
        # Quoted Charges Analysis (like Billing Report)
        {"label": "Quoted Revenue", "fieldname": "quoted_revenue", "fieldtype": "Currency", "width": 110},
        {"label": "Quoted Cost", "fieldname": "quoted_cost", "fieldtype": "Currency", "width": 110},
        {"label": "Quoted Profit", "fieldname": "quoted_profit", "fieldtype": "Currency", "width": 110},
        {"label": "Quoted Margin %", "fieldname": "quoted_margin", "fieldtype": "Percent", "width": 95},
        
        # Working Charges Analysis
        {"label": "Working Revenue", "fieldname": "working_revenue", "fieldtype": "Currency", "width": 110},
        {"label": "Working Cost", "fieldname": "working_cost", "fieldtype": "Currency", "width": 110},
        {"label": "Working Profit", "fieldname": "working_profit", "fieldtype": "Currency", "width": 110},
        {"label": "Working Margin %", "fieldname": "working_margin", "fieldtype": "Percent", "width": 95},
        
        # Invoiced Charges Analysis
        {"label": "Invoiced Revenue", "fieldname": "invoiced_revenue", "fieldtype": "Currency", "width": 110},
        {"label": "Invoiced Cost", "fieldname": "invoiced_cost", "fieldtype": "Currency", "width": 110},
        {"label": "Invoiced Profit", "fieldname": "invoiced_profit", "fieldtype": "Currency", "width": 110},
        {"label": "Invoiced Margin %", "fieldname": "invoiced_margin", "fieldtype": "Percent", "width": 95},
        
        # Variance Analysis
        {"label": "Revenue Variance", "fieldname": "revenue_variance", "fieldtype": "Currency", "width": 110},
        {"label": "Cost Variance", "fieldname": "cost_variance", "fieldtype": "Currency", "width": 110},
        {"label": "Profit Variance", "fieldname": "profit_variance", "fieldtype": "Currency", "width": 110},
    ]
    return columns

def execute(filters=None):
    """Main execution function - standalone implementation."""
    if not filters:
        filters = {}
    
    # Get columns
    columns = get_columns()
    data = []
    
    # Build conditions for SQL query with essential filtering
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
    
    # Get comprehensive data from database using direct SQL for better performance
    jobs = frappe.db.sql(f"""
        SELECT name, date_created, customer, customer_reference, direction, status,
               shipment_mode, shipment_type, cargo_description, cargo_count,
               shipper, consignee, notify_party,
               port_of_loading, port_of_discharge, destination, 
               origin_country, destination_country,
               vessel_flight_no, vessel_flight_date,
               booking_date, cargo_ready_date, etd, eta, atd, ata, 
               discharge_date, completed_on,
               bl_number, bl_type, bl_issued_date, is_bl_received, bl_received_date, 
               is_bl_confirmed, bl_confirmed_date,
               incoterms, incoterm_place, currency, conversion_rate,
               is_trucking_required, trucks_required,
               total_quoted_revenue_base, total_quoted_cost_base, 
               total_quoted_profit_base, quoted_margin_percent,
               total_working_revenue_base, total_working_cost, 
               total_working_profit_base, profit_margin_percent
        FROM `tabForwarding Job`
        WHERE {conditions}
        ORDER BY date_created DESC
    """, as_dict=True)
    
    # Process comprehensive data with charges analysis
    for job in jobs:
        # Combine direction and shipment mode
        direction = job.get("direction", "")
        shipment_mode = job.get("shipment_mode", "")
        combined_direction = f"{shipment_mode} {direction}" if shipment_mode and direction else (shipment_mode or direction or "")
        
        # Quoted figures
        quoted_revenue = job.get("total_quoted_revenue_base", 0)
        quoted_cost = job.get("total_quoted_cost_base", 0)
        quoted_profit = job.get("total_quoted_profit_base", 0)
        quoted_margin = job.get("quoted_margin_percent", 0)
        
        # Working figures
        working_revenue = job.get("total_working_revenue_base", 0)
        working_cost = job.get("total_working_cost", 0)
        working_profit = job.get("total_working_profit_base", 0)
        working_margin = job.get("profit_margin_percent", 0)
        
        # Invoiced Revenue (Sales Invoice)
        invoiced_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference = %s
        """, (job["name"]))[0][0] or 0
        
        # Invoiced Cost (Purchase Invoice)
        invoiced_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference = %s
        """, (job["name"]))[0][0] or 0
        
        # Invoiced Profit & Margin
        invoiced_profit = invoiced_revenue - invoiced_cost
        invoiced_margin = (invoiced_profit / invoiced_revenue * 100) if invoiced_revenue else 0
        
        # Variance Analysis
        revenue_variance = invoiced_revenue - quoted_revenue
        cost_variance = invoiced_cost - quoted_cost
        profit_variance = invoiced_profit - quoted_profit
        
        data.append({
            # Core Job Information
            "job_id": job.get("name", ""),
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "direction": combined_direction,
            "status": job.get("status", ""),
            
            # Shipment Details
            "shipment_mode": job.get("shipment_mode", ""),
            "shipment_type": job.get("shipment_type", ""),
            "cargo_description": job.get("cargo_description", ""),
            "cargo_count": job.get("cargo_count", ""),
            
            # Parties
            "shipper": job.get("shipper", ""),
            "consignee": job.get("consignee", ""),
            "notify_party": job.get("notify_party", ""),
            
            # Routing Information
            "port_of_loading": job.get("port_of_loading", ""),
            "port_of_discharge": job.get("port_of_discharge", ""),
            "destination": job.get("destination", ""),
            "origin_country": job.get("origin_country", ""),
            "destination_country": job.get("destination_country", ""),
            
            # Transport Details
            "vessel_flight_no": job.get("vessel_flight_no", ""),
            "vessel_flight_date": format_date(job.get("vessel_flight_date")),
            
            # Important Dates
            "booking_date": format_date(job.get("booking_date")),
            "cargo_ready_date": format_date(job.get("cargo_ready_date")),
            "etd": format_date(job.get("etd")),
            "atd": format_date(job.get("atd")),
            "eta": format_date(job.get("eta")),
            "ata": format_date(job.get("ata")),
            "discharge_date": format_date(job.get("discharge_date")),
            "completed_on": format_date(job.get("completed_on")),
            
            # Bill of Lading Information
            "bl_number": job.get("bl_number", ""),
            "bl_type": job.get("bl_type", ""),
            "bl_issued_date": format_date(job.get("bl_issued_date")),
            "is_bl_received": format_checkbox(job.get("is_bl_received", 0)),
            "bl_received_date": format_date(job.get("bl_received_date")),
            "is_bl_confirmed": format_checkbox(job.get("is_bl_confirmed", 0)),
            "bl_confirmed_date": format_date(job.get("bl_confirmed_date")),
            
            # Trade Terms
            "incoterms": job.get("incoterms", ""),
            "incoterm_place": job.get("incoterm_place", ""),
            
            # Currency Information
            "currency": job.get("currency", ""),
            "conversion_rate": job.get("conversion_rate", 0),
            
            # Trucking Information
            "is_trucking_required": format_checkbox(job.get("is_trucking_required", 0)),
            "trucks_required": job.get("trucks_required", ""),
            
            # Quoted Charges Analysis
            "quoted_revenue": quoted_revenue,
            "quoted_cost": quoted_cost,
            "quoted_profit": quoted_profit,
            "quoted_margin": quoted_margin,
            
            # Working Charges Analysis
            "working_revenue": working_revenue,
            "working_cost": working_cost,
            "working_profit": working_profit,
            "working_margin": working_margin,
            
            # Invoiced Charges Analysis
            "invoiced_revenue": invoiced_revenue,
            "invoiced_cost": invoiced_cost,
            "invoiced_profit": invoiced_profit,
            "invoiced_margin": invoiced_margin,
            
            # Variance Analysis
            "revenue_variance": revenue_variance,
            "cost_variance": cost_variance,
            "profit_variance": profit_variance,
        })
    
    return columns, data

def format_checkbox(value):
    """Format checkbox value for display."""
    return "Yes" if value else "No"

def format_date(date_value):
    """Format date string to dd-MMM-yy format."""
    if not date_value:
        return ""
    try:
        return formatdate(date_value, "dd-MMM-yy")
    except Exception:
        return date_value
