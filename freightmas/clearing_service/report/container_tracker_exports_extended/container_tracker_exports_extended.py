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
        {"label": "Cargo Desc", "fieldname": "cargo_description", "fieldtype": "Data", "width": 180},
        {"label": "Container No", "fieldname": "container_number", "fieldtype": "Data", "width": 140},
        {"label": "Type", "fieldname": "container_type", "fieldtype": "Data", "width": 90},
        {"label": "DnD Free Dys", "fieldname": "dnd_free_days", "fieldtype": "Int", "width": 80},
        {"label": "Port Free Dys", "fieldname": "port_free_days", "fieldtype": "Int", "width": 80},
        {"label": "Empty Picked", "fieldname": "is_empty_picked", "fieldtype": "Data", "width": 60},
        {"label": "Pick Empty Date", "fieldname": "pick_up_empty_date", "fieldtype": "Data", "width": 110},
        {"label": "Gated In", "fieldname": "is_gated_in_port", "fieldtype": "Data", "width": 60},
        {"label": "Gated In Date", "fieldname": "gate_in_full_date", "fieldtype": "Data", "width": 110},
        {"label": "Loaded on Vessel", "fieldname": "is_loaded_on_vessel", "fieldtype": "Data", "width": 60},
        {"label": "Loaded Date", "fieldname": "loaded_on_vessel_date", "fieldtype": "Data", "width": 110},
        {"label": "Transporter", "fieldname": "transporter_name", "fieldtype": "Data", "width": 120},
        {"label": "Truck Reg", "fieldname": "truck_reg_no", "fieldtype": "Data", "width": 100},
        {"label": "Trailer Reg", "fieldname": "trailer_reg_no", "fieldtype": "Data", "width": 100},
        {"label": "Driver Name", "fieldname": "driver_name", "fieldtype": "Data", "width": 100},
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

    # Only show exports
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
            "shipping_line", "bl_number", "dnd_free_days", "port_free_days", "cargo_description"
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
                "is_empty_picked",
                "pick_up_empty_date",
                "is_gated_in_port",
                "gate_in_full_date",
                "is_loaded_on_vessel",
                "loaded_on_vessel_date",
                "transporter_name",
                "truck_reg_no",
                "trailer_reg_no",
                "driver_name"
            ]
        )

        for cont in containers:
            # Status logic
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

            # DND/Storage logic
            dnd_free_days = int(job.get("dnd_free_days") or 0)
            port_free_days = int(job.get("port_free_days") or 0)
            today_dt = frappe.utils.getdate(frappe.utils.nowdate())
            pick_up_empty_dt = frappe.utils.getdate(pick_up_empty_date) if pick_up_empty_date else None
            gate_in_full_dt = frappe.utils.getdate(gate_in_full_date) if gate_in_full_date else None
            loaded_on_vessel_dt = frappe.utils.getdate(cont.get("loaded_on_vessel_date")) if cont.get("loaded_on_vessel_date") else None

            end_date = loaded_on_vessel_dt if is_loaded_on_vessel and loaded_on_vessel_dt else today_dt

            dnd_days = (end_date - pick_up_empty_dt).days - dnd_free_days if pick_up_empty_dt else 0
            dnd_days = max(dnd_days, 0)
            storage_days = (end_date - gate_in_full_dt).days - port_free_days if gate_in_full_dt else 0
            storage_days = max(storage_days, 0)

            # --- Filter by Status if provided ---
            if filters.get("status") and container_status != filters["status"]:
                continue

            data.append({
                "name": job["name"],
                "date_created": format_date(job["date_created"]),
                "customer": job["customer"],
                "shipping_line": job.get("shipping_line", ""),
                "bl_number": job.get("bl_number", ""),
                "cargo_description": job.get("cargo_description", ""),
                "container_number": cont.get("container_number", ""),
                "container_type": cont.get("container_type", ""),
                "dnd_free_days": dnd_free_days,
                "port_free_days": port_free_days,
                "is_empty_picked": "Yes" if cont.get("is_empty_picked") else "No",
                "pick_up_empty_date": format_date(cont.get("pick_up_empty_date")),
                "is_gated_in_port": "Yes" if cont.get("is_gated_in_port") else "No",
                "gate_in_full_date": format_date(cont.get("gate_in_full_date")),
                "is_loaded_on_vessel": "Yes" if cont.get("is_loaded_on_vessel") else "No",
                "loaded_on_vessel_date": format_date(cont.get("loaded_on_vessel_date")),
                "transporter_name": cont.get("transporter_name", ""),
                "truck_reg_no": cont.get("truck_reg_no", ""),
                "trailer_reg_no": cont.get("trailer_reg_no", ""),
                "driver_name": cont.get("driver_name", ""),
                "container_status": container_status,
                "dnd_days": dnd_days,
                "storage_days": storage_days,
            })

    return columns, data
