# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from freightmas.utils.dnd_storage_days import calculate_dnd_and_storage_days


def format_date(date_str):
    if not date_str:
        return ""
    try:
        return frappe.utils.formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str


def execute(filters=None):
    columns = [
        {"label": "Job No", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 260},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 95},
        {"label": "Cargo Count", "fieldname": "cargo_count", "fieldtype": "Data", "width": 120},
        {"label": "Disch Date", "fieldname": "discharge_date", "fieldtype": "Data", "width": 100},
        {"label": "DnD Start", "fieldname": "dnd_start_date", "fieldtype": "Data", "width": 100},
        {"label": "Stor Start", "fieldname": "storage_start_date", "fieldtype": "Data", "width": 100},
        {"label": "DnD Days", "fieldname": "total_dnd_days", "fieldtype": "Int", "width": 95},
        {"label": "Stor Days", "fieldname": "total_storage_days", "fieldtype": "Int", "width": 90},
    ]
    data = []

    filters = filters or {}
    job_filters = {}

    # Date filter (if provided)
    if filters.get("from_date") and filters.get("to_date"):
        job_filters["date_created"] = ["between", [filters["from_date"], filters["to_date"]]]
    if filters.get("customer"):
        job_filters["customer"] = filters["customer"]
    if filters.get("job_no"):
        job_filters["name"] = filters["job_no"]
    if filters.get("direction") and filters["direction"].strip():
        job_filters["direction"] = filters["direction"]

    jobs = frappe.get_all(
        "Clearing Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "direction", "cargo_count", "discharge_date",
            "dnd_start_date", "storage_start_date",
            "dnd_free_days", "port_free_days"
        ]
    )

    for job in jobs:
        # Fetch cargo packages for this job
        cargo_packages = frappe.get_all(
            "Cargo Package Details",
            filters={"parent": job["name"], "parenttype": "Clearing Job"},
            fields=[
                "to_be_returned", "is_loaded", "is_returned",
                "gate_in_empty_date", "gate_out_full_date",
                "pick_up_empty_date", "gate_in_full_date",
                "is_loaded_on_vessel", "loaded_on_vessel_date"
            ]
        )

        total_dnd_days, total_storage_days = calculate_dnd_and_storage_days(job, cargo_packages)

        data.append({
            "name": job["name"],
            "date_created": format_date(job["date_created"]),
            "customer": job["customer"],
            "direction": job.get("direction", ""),
            "cargo_count": job.get("cargo_count", ""),
            "discharge_date": format_date(job.get("discharge_date")),
            "dnd_start_date": format_date(job.get("dnd_start_date")),
            "storage_start_date": format_date(job.get("storage_start_date")),
            "total_dnd_days": total_dnd_days,
            "total_storage_days": total_storage_days,
        })

    return columns, data





