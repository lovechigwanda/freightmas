# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def format_date(date_str):
    if not date_str:
        return ""
    try:
        return frappe.utils.formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str

def get_columns():
    return [
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 90},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 120},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 120},
        {"label": "Type", "fieldname": "shipment_type", "fieldtype": "Data", "width": 60},
        {"label": "Cargo Desc.", "fieldname": "cargo_description", "fieldtype": "Data", "width": 150, "align": "left"},
        {"label": "Shipper", "fieldname": "shipper", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"label": "Origin", "fieldname": "port_of_loading", "fieldtype": "Link", "options": "Port", "width": 120},
        {"label": "Disch Port", "fieldname": "port_of_discharge", "fieldtype": "Link", "options": "Port", "width": 120},
        {"label": "Destination", "fieldname": "destination", "fieldtype": "Link", "options": "Port", "width": 120},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 120},
        {"label": "BL Type", "fieldname": "bl_type", "fieldtype": "Data", "width": 80},
        {"label": "Vess/Flt", "fieldname": "vessel_flight_no", "fieldtype": "Data", "width": 100},
        {"label": "Bkng Date", "fieldname": "booking_date", "fieldtype": "Data", "width": 100},
        {"label": "Cargo Ready", "fieldname": "cargo_ready_date", "fieldtype": "Data", "width": 100},
        {"label": "ETD", "fieldname": "etd", "fieldtype": "Data", "width": 90},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 90},
        {"label": "ATD", "fieldname": "atd", "fieldtype": "Data", "width": 90},
        {"label": "ATA", "fieldname": "ata", "fieldtype": "Data", "width": 90},
        {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "Data", "width": 100},
        {"label": "BL Recvd", "fieldname": "is_bl_received", "fieldtype": "Check", "width": 80},
        {"label": "BL Confmd", "fieldname": "is_bl_confirmed", "fieldtype": "Check", "width": 80},
        {"label": "Incoterms", "fieldname": "incoterms", "fieldtype": "Link", "options": "Incoterm", "width": 80},
        {"label": "Est. Rev", "fieldname": "total_quoted_revenue_base", "fieldtype": "Currency", "width": 110},
        {"label": "Est. Cost", "fieldname": "total_quoted_cost_base", "fieldtype": "Currency", "width": 110},
        {"label": "Est. Prft", "fieldname": "total_quoted_profit_base", "fieldtype": "Currency", "width": 110},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": "Completed", "fieldname": "completed_on", "fieldtype": "Data", "width": 100},
    ]

def execute(filters=None):
    columns = get_columns()
    data = []

    filters = filters or {}
    job_filters = {}

    if filters.get("from_date") and filters.get("to_date"):
        job_filters["date_created"] = ["between", [filters["from_date"], filters["to_date"]]]
    if filters.get("customer"):
        job_filters["customer"] = filters["customer"]
    if filters.get("status"):
        job_filters["status"] = filters["status"]

    jobs = frappe.get_all(
        "Forwarding Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference", "direction", "shipment_mode",
            "shipment_type", "cargo_description", "shipper", "consignee",
            "port_of_loading", "port_of_discharge", "destination", "bl_number", "bl_type",
            "vessel_flight_no", "booking_date", "cargo_ready_date", "etd", "eta", "atd", "ata", 
            "delivery_date", "is_bl_received", "is_bl_confirmed", "incoterms",
            "total_quoted_revenue_base", "total_quoted_cost_base", "total_quoted_profit_base",
            "status", "completed_on"
        ]
    )

    for job in jobs:
        # Combine shipment_mode + direction for the Direction field
        combined_direction = ""
        if job.get("shipment_mode") and job.get("direction"):
            combined_direction = f"{job.get('shipment_mode')} {job.get('direction')}"
        elif job.get("shipment_mode"):
            combined_direction = job.get("shipment_mode")
        elif job.get("direction"):
            combined_direction = job.get("direction")

        data.append({
            "name": job.get("name", ""),
            "date_created": format_date(job["date_created"]),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "direction": combined_direction,
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
            "booking_date": format_date(job.get("booking_date", "")),
            "cargo_ready_date": format_date(job.get("cargo_ready_date", "")),
            "etd": format_date(job.get("etd", "")),
            "eta": format_date(job.get("eta", "")),
            "atd": format_date(job.get("atd", "")),
            "ata": format_date(job.get("ata", "")),
            "delivery_date": format_date(job.get("delivery_date", "")),
            "is_bl_received": job.get("is_bl_received", 0),
            "is_bl_confirmed": job.get("is_bl_confirmed", 0),
            "incoterms": job.get("incoterms", ""),
            "total_quoted_revenue_base": job.get("total_quoted_revenue_base", 0),
            "total_quoted_cost_base": job.get("total_quoted_cost_base", 0),
            "total_quoted_profit_base": job.get("total_quoted_profit_base", 0),
            "status": job.get("status", ""),
            "completed_on": format_date(job.get("completed_on", "")),
        })

    return columns, data
