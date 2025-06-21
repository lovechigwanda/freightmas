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
        {"label": "Job No", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 210},
        {"label": "S Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Shipping Line", "width": 90},
        {"label": "BL No", "fieldname": "bl_number", "fieldtype": "Data", "width": 140},
        {"label": "Container No", "fieldname": "container_number", "fieldtype": "Data", "width": 140},
        {"label": "Type", "fieldname": "container_type", "fieldtype": "Data", "width": 90},
        {"label": "Status", "fieldname": "container_status", "fieldtype": "Data", "width": 120},
        {"label": "D Days", "fieldname": "dnd_days", "fieldtype": "Int", "width": 75},
        {"label": "S Days", "fieldname": "storage_days", "fieldtype": "Int", "width": 75},
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
    if filters.get("bl_number"):
        job_filters["bl_number"] = ["like", f"%{filters['bl_number']}%"]

    # Only show imports
    job_filters["direction"] = "Import"

    # --- Get job names with at least one containerised cargo package ---
    containerised_jobs = frappe.get_all(
        "Cargo Package Details",
        filters={"cargo_type": "Containerised", "parenttype": "Clearing Job"},
        fields=["parent"],
        distinct=True
    )
    containerised_job_names = [row["parent"] for row in containerised_jobs]
    if containerised_job_names:
        job_filters["name"] = ["in", containerised_job_names]
    else:
        return columns, []

    jobs = frappe.get_all(
        "Clearing Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "direction",
            "shipping_line", "bl_number", "discharge_date", "dnd_free_days", "port_free_days"
        ]
    )

    for job in jobs:
        container_filters = {
            "parent": job["name"],
            "parenttype": "Clearing Job",
            "cargo_type": "Containerised"
        }

        if filters.get("container_no"):
            container_filters["container_number"] = ["like", f"%{filters['container_no']}%"]

        containers = frappe.get_all(
            "Cargo Package Details",
            filters=container_filters,
            fields=[
                "name", "container_number", "container_type", "is_loaded", "to_be_returned", "is_returned",
                "gate_in_empty_date", "gate_out_full_date"
            ]
        )

        for cont in containers:
            # Per-container DND/Storage days logic for imports
            to_be_returned = int(cont.get("to_be_returned") or 0)
            is_loaded = int(cont.get("is_loaded") or 0)
            is_returned = int(cont.get("is_returned") or 0)
            gate_in_empty_date = frappe.utils.getdate(cont.get("gate_in_empty_date"))
            gate_out_full_date = frappe.utils.getdate(cont.get("gate_out_full_date"))
            discharge_date = frappe.utils.getdate(job.get("discharge_date"))
            dnd_free_days = int(job.get("dnd_free_days") or 0)
            port_free_days = int(job.get("port_free_days") or 0)
            today_dt = frappe.utils.getdate(frappe.utils.nowdate())

            # DND end date logic
            if to_be_returned:
                if is_loaded and is_returned and gate_in_empty_date:
                    dnd_end_date = gate_in_empty_date
                else:
                    dnd_end_date = today_dt
            else:
                if is_loaded and gate_out_full_date:
                    dnd_end_date = gate_out_full_date
                else:
                    dnd_end_date = today_dt

            # Storage end date logic
            if not is_loaded:
                storage_end_date = today_dt
            elif is_loaded and gate_out_full_date:
                storage_end_date = gate_out_full_date
            else:
                storage_end_date = today_dt

            # DND days
            if dnd_end_date and discharge_date:
                dnd_days = (dnd_end_date - discharge_date).days - dnd_free_days
                dnd_days = max(dnd_days, 0)
            else:
                dnd_days = 0

            # Storage days
            if storage_end_date and discharge_date:
                storage_days = (storage_end_date - discharge_date).days - port_free_days
                storage_days = max(storage_days, 0)
            else:
                storage_days = 0

            # Container status logic
            if (to_be_returned == 1 and is_loaded == 0 and is_returned == 0) or (to_be_returned == 0 and is_loaded == 0 and is_returned == 0):
                container_status = "In Port"
            elif to_be_returned == 1 and is_loaded == 1 and is_returned == 0:
                container_status = "Not Returned"
            elif to_be_returned == 1 and is_loaded == 1 and is_returned == 1:
                container_status = "Returned"
            elif to_be_returned == 0 and is_loaded == 1 and is_returned == 0:
                container_status = "Delivered"
            else:
                container_status = ""

            # --- Filter by Status if provided ---
            if filters.get("status") and container_status != filters["status"]:
                continue

            data.append({
                "name": job["name"],
                "date_created": format_date(job["date_created"]),
                "customer": job["customer"],
                "shipping_line": job.get("shipping_line", ""),
                "bl_number": job.get("bl_number", ""),
                "container_number": cont.get("container_number", ""),
                "container_type": cont.get("container_type", ""),
                "dnd_days": dnd_days,
                "storage_days": storage_days,
                "container_status": container_status,
            })

    return columns, data





