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
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Road Freight Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 90},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 160},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 90},
        {"label": "Type", "fieldname": "shipment_type", "fieldtype": "Data", "width": 110},
        {"label": "Cargo Desc.", "fieldname": "cargo_description", "fieldtype": "Data", "width": 180, "align": "left"},
        {"label": "Load At", "fieldname": "port_of_loading", "fieldtype": "Link", "options": "Port", "width": 100},
        {"label": "Offload At", "fieldname": "port_of_discharge", "fieldtype": "Link", "options": "Port", "width": 100},
        {"label": "Drop At", "fieldname": "empty_drop_off_at", "fieldtype": "Link", "options": "Port", "width": 100},
        {"label": "No Req", "fieldname": "no_of_trucks_required", "fieldtype": "Int", "width": 90},
        {"label": "No Conf", "fieldname": "trucks_confirmed", "fieldtype": "Int", "width": 90},
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
        "Road Freight Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference", "direction", "shipment_type",
            "cargo_description", "port_of_loading", "port_of_discharge", "empty_drop_off_at",
            "no_of_trucks_required", "trucks_confirmed",
            "total_estimated_revenue_base", "total_estimated_cost_base", "total_estimated_profit_base",
            "status"
        ]
    )

    for job in jobs:
        data.append({
            "name": job.get("name", ""),
            "date_created": format_date(job["date_created"]),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "direction": job.get("direction", ""),
            "shipment_type": job.get("shipment_type", ""),
            "cargo_description": job.get("cargo_description", ""),
            "port_of_loading": job.get("port_of_loading", ""),
            "port_of_discharge": job.get("port_of_discharge", ""),
            "empty_drop_off_at": job.get("empty_drop_off_at", ""),
            "no_of_trucks_required": job.get("no_of_trucks_required", 0),
            "trucks_confirmed": job.get("trucks_confirmed", 0),
            "total_estimated_revenue_base": job.get("total_estimated_revenue_base", 0),
            "total_estimated_cost_base": job.get("total_estimated_cost_base", 0),
            "total_estimated_profit_base": job.get("total_estimated_profit_base", 0),
            "status": job.get("status", ""),
        })

    return columns, data
