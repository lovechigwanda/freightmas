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
        {"label": "D&D Free Dys", "fieldname": "dnd_free_days", "fieldtype": "Int", "width": 80},
        {"label": "Port Free Dys", "fieldname": "port_free_days", "fieldtype": "Int", "width": 80},
        {"label": "Disch Date", "fieldname": "discharge_date", "fieldtype": "Data", "width": 110},
        {"label": "Returning", "fieldname": "to_be_returned", "fieldtype": "Data", "width": 60},
        {"label": "Loaded", "fieldname": "is_loaded", "fieldtype": "Data", "width": 60},
        {"label": "Out Date", "fieldname": "gate_out_full_date", "fieldtype": "Data", "width": 110},
        {"label": "Returned", "fieldname": "is_returned", "fieldtype": "Data", "width": 60},
        {"label": "In Date", "fieldname": "gate_in_empty_date", "fieldtype": "Data", "width": 110},
        {"label": "Transporter", "fieldname": "transporter_name", "fieldtype": "Data", "width": 120},
        {"label": "Truck Reg", "fieldname": "truck_reg_no", "fieldtype": "Data", "width": 100},
        {"label": "Trailer Reg", "fieldname": "trailer_reg_no", "fieldtype": "Data", "width": 100},
        {"label": "Driver Name", "fieldname": "driver_name", "fieldtype": "Data", "width": 100},
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
            "shipping_line", "bl_number", "discharge_date", "dnd_free_days", "port_free_days", "cargo_description"
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
                "name", "container_number", "container_type", "to_be_returned", "is_loaded", "gate_out_full_date",
                "is_returned", "gate_in_empty_date", "transporter_name", "truck_reg_no", "trailer_reg_no", "driver_name"
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
                "cargo_description": job.get("cargo_description", ""),
                "container_number": cont.get("container_number", ""),
                "container_type": cont.get("container_type", ""),
                "dnd_free_days": job.get("dnd_free_days", 0),
                "port_free_days": job.get("port_free_days", 0),
                "discharge_date": format_date(job.get("discharge_date")),
                "to_be_returned": "Yes" if cont.get("to_be_returned") else "No",
                "is_loaded": "Yes" if cont.get("is_loaded") else "No",
                "gate_out_full_date": format_date(cont.get("gate_out_full_date")),
                "is_returned": "Yes" if cont.get("is_returned") else "No",
                "gate_in_empty_date": format_date(cont.get("gate_in_empty_date")),
                "transporter_name": cont.get("transporter_name", ""),
                "truck_reg_no": cont.get("truck_reg_no", ""),
                "trailer_reg_no": cont.get("trailer_reg_no", ""),
                "driver_name": cont.get("driver_name", ""),
                "container_status": container_status,
                "dnd_days": dnd_days,
                "storage_days": storage_days,
            })

    return columns, data





