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
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 120},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 120},
        {"label": "Port of Loading", "fieldname": "port_of_loading", "fieldtype": "Link", "options": "Port", "width": 120},
        {"label": "Final Destination", "fieldname": "destination", "fieldtype": "Link", "options": "Port", "width": 120},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 120},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 90},
        {"label": "Est. Rev", "fieldname": "total_estimated_revenue_base", "fieldtype": "Currency", "width": 110},
        {"label": "Est. Cost", "fieldname": "total_estimated_cost_base", "fieldtype": "Currency", "width": 110},
        {"label": "Est. Prft", "fieldname": "total_estimated_profit_base", "fieldtype": "Currency", "width": 110},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
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
            "port_of_loading", "destination", "bl_number", "eta",
            "total_estimated_revenue_base", "total_estimated_cost_base", "total_estimated_profit_base",
            "status"
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
            "port_of_loading": job.get("port_of_loading", ""),
            "destination": job.get("destination", ""),
            "bl_number": job.get("bl_number", ""),
            "eta": format_date(job.get("eta")),
            "total_estimated_revenue_base": job.get("total_estimated_revenue_base", 0),
            "total_estimated_cost_base": job.get("total_estimated_cost_base", 0),
            "total_estimated_profit_base": job.get("total_estimated_profit_base", 0),
            "status": job.get("status", ""),
        })

    return columns, data
