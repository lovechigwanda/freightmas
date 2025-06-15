# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe

from __future__ import unicode_literals
import frappe
from freightmas.utils.dnd_storage_days_per_container import calculate_dnd_and_storage_days_detailed

def format_date(date_str):
    if not date_str:
        return ""
    try:
        return frappe.utils.formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str

def get_columns():
    return [
        {"label": "Job No", "fieldname": "job_no", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Job Date", "fieldname": "job_date", "fieldtype": "Date", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 220},
        {"label": "Shipping Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Shipping Line", "width": 160},
        {"label": "BL No", "fieldname": "bl_number", "fieldtype": "Data", "width": 120},
        {"label": "Container No", "fieldname": "container_no", "fieldtype": "Data", "width": 120},
        {"label": "Disch Date", "fieldname": "discharge_date", "fieldtype": "Date", "width": 100},
        {"label": "DND Days", "fieldname": "dnd_days", "fieldtype": "Int", "width": 95},
        {"label": "Storage Days", "fieldname": "storage_days", "fieldtype": "Int", "width": 90},
        {"label": "Container Status", "fieldname": "container_status", "fieldtype": "Data", "width": 120},
    ]

def execute(filters=None):
    columns = get_columns()
    data = []

    filters = filters or {}
    job_filters = {}

    # Date filter (if provided)
    if filters.get("from_date") and filters.get("to_date"):
        job_filters["date_created"] = ["between", [filters["from_date"], filters["to_date"]]]
    if filters.get("customer"):
        job_filters["customer"] = filters["customer"]
    if filters.get("shipping_line"):
        job_filters["shipping_line"] = filters["shipping_line"]
    if filters.get("bl_number"):
        job_filters["bl_number"] = ["like", f"%{filters['bl_number']}%"]
    if filters.get("job_no"):
        job_filters["name"] = filters["job_no"]

    # Only containerised cargo
    job_filters["cargo_type"] = "Containerised"

    jobs = frappe.get_all(
        "Clearing Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "shipping_line", "bl_number", "discharge_date", "dnd_free_days", "port_free_days"
        ]
    )

    for job in jobs:
        containers = frappe.get_all(
            "Cargo Package Details",
            filters={"parent": job["name"], "parenttype": "Clearing Job", "cargo_type": "Containerised"},
            fields=[
                "name", "container_number", "to_be_returned", "is_loaded", "is_returned",
                "gate_in_empty_date", "gate_out_full_date", "pick_up_empty_date", "gate_in_full_date",
                "is_loaded_on_vessel", "loaded_on_vessel_date"
            ]
        )

        # Only process unique, non-empty container numbers
        seen = set()
        _, _, breakdown = calculate_dnd_and_storage_days_detailed(job, containers)
        breakdown_map = {b["cargo_package"]: b for b in breakdown}
        for cont in containers:
            container_no = cont.get("container_number", "")
            if not container_no or container_no in seen:
                continue
            seen.add(container_no)
            dnd_days = breakdown_map.get(cont["name"], {}).get("dnd_days", 0)
            storage_days = breakdown_map.get(cont["name"], {}).get("storage_days", 0)
            # Container Status logic
            if not cont.get("is_loaded"):
                status = "In Port"
            elif cont.get("to_be_returned") and cont.get("is_loaded"):
                status = "Not Returned"
            elif cont.get("is_returned"):
                status = "Returned"
            else:
                status = ""
            data.append({
                "job_no": job["name"],
                "job_date": format_date(job["date_created"]),
                "customer": job["customer"],
                "shipping_line": job["shipping_line"],
                "bl_number": job["bl_number"],
                "container_no": container_no,
                "discharge_date": format_date(job.get("discharge_date")),
                "dnd_days": dnd_days,
                "storage_days": storage_days,
                "container_status": status
            })

    return columns, data