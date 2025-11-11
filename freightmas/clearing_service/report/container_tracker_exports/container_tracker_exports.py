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
        {"label": "BL No", "fieldname": "bl_number", "fieldtype": "Data", "width": 160},
        {"label": "Container No", "fieldname": "container_number", "fieldtype": "Data", "width": 140},
        {"label": "Type", "fieldname": "container_type", "fieldtype": "Data", "width": 90},
        {"label": "Status", "fieldname": "container_status", "fieldtype": "Data", "width": 140},
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
    job_filters["direction"] = "Export"

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
                "name",
                "container_number",
                "container_type",
                "is_loaded",
                "to_be_returned",
                "is_returned",
                "gate_in_empty_date",
                "gate_out_full_date",
                "pick_up_empty_date",         # <-- Add this
                "gate_in_full_date",          # <-- Add this
                "is_loaded_on_vessel",        # <-- Add this
                "loaded_on_vessel_date"       # <-- Add this
            ]
        )

        for cont in containers:
            pick_up_empty_date = cont.get("pick_up_empty_date")
            gate_in_full_date = cont.get("gate_in_full_date")
            is_loaded_on_vessel = int(cont.get("is_loaded_on_vessel") or 0)

            if not pick_up_empty_date:
                container_status = "Not Yet Picked"
            elif pick_up_empty_date and not gate_in_full_date:
                container_status = "Not Yet Gated In"
            elif gate_in_full_date and not is_loaded_on_vessel:
                container_status = "In Port"
            elif is_loaded_on_vessel:
                container_status = "Loaded on Vessel"
            else:
                container_status = "Unknown"

            # --- Filter by Status if provided ---
            if filters.get("status") and container_status != filters["status"]:
                continue

            # --- Export logic ---
            pick_up_empty_date = frappe.utils.getdate(cont.get("pick_up_empty_date"))
            gate_in_full_date = frappe.utils.getdate(cont.get("gate_in_full_date"))
            loaded_on_vessel_date = frappe.utils.getdate(cont.get("loaded_on_vessel_date"))
            dnd_free_days = int(job.get("dnd_free_days") or 0)
            port_free_days = int(job.get("port_free_days") or 0)
            today_dt = frappe.utils.getdate(frappe.utils.nowdate())

            # DND and Storage end date logic for exports
            end_date = loaded_on_vessel_date if is_loaded_on_vessel and loaded_on_vessel_date else today_dt

            # DND days: from pick_up_empty_date to end_date
            if pick_up_empty_date:
                dnd_days = (end_date - pick_up_empty_date).days - dnd_free_days
                dnd_days = max(dnd_days, 0)
            else:
                dnd_days = 0

            # Storage days: from gate_in_full_date to end_date
            if gate_in_full_date:
                storage_days = (end_date - gate_in_full_date).days - port_free_days
                storage_days = max(storage_days, 0)
            else:
                storage_days = 0

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





