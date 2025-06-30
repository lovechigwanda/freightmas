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
    columns = get_columns()
    data = []

    filters = filters or {}
    job_filters = {}

    # Filter for import jobs only
    job_filters["direction"] = "Import"

    # Additional filters
    if filters.get("from_date") and filters.get("to_date"):
        job_filters["date_created"] = ["between", [filters["from_date"], filters["to_date"]]]
    if filters.get("customer"):
        job_filters["customer"] = filters["customer"]
    if filters.get("bl_number"):
        job_filters["bl_number"] = ["like", f"%{filters['bl_number']}%"]

    jobs = frappe.get_all(
        "Clearing Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "consignee",
            "shipping_line", "bl_number", "cargo_count",
            "dnd_start_date", "storage_start_date",
            "bl_received_date", "bl_confirmed_date", "vessel_arrived_date",
            "sl_invoice_received_date", "sl_invoice_payment_date",
            "date_discharged_from_port", "do_requested_date", "do_received_date",
            "port_release_confirmed_date",
            "status", "completed_on",
            # Fields needed for DnD/Storage calculation
            "discharge_date", "dnd_free_days", "port_free_days"
        ]
    )

    for job in jobs:
        # Fetch cargo packages for this job (for DnD/Storage calculation)
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
            "consignee": job.get("consignee", ""),
            "shipping_line": job.get("shipping_line", ""),
            "bl_number": job.get("bl_number", ""),
            "cargo_count": job.get("cargo_count", ""),
            "dnd_start_date": format_date(job.get("dnd_start_date")),
            "storage_start_date": format_date(job.get("storage_start_date")),
            "bl_received_date": format_date(job.get("bl_received_date")),
            "bl_confirmed_date": format_date(job.get("bl_confirmed_date")),
            "vessel_arrived_date": format_date(job.get("vessel_arrived_date")),
            "sl_invoice_received_date": format_date(job.get("sl_invoice_received_date")),
            "sl_invoice_payment_date": format_date(job.get("sl_invoice_payment_date")),
            "date_discharged_from_port": format_date(job.get("date_discharged_from_port")),
            "do_requested_date": format_date(job.get("do_requested_date")),
            "do_received_date": format_date(job.get("do_received_date")),
            "port_release_confirmed_date": format_date(job.get("port_release_confirmed_date")),
            "total_dnd_days": total_dnd_days,
            "total_storage_days": total_storage_days,
            "status": job.get("status", ""),
            "completed_on": format_date(job.get("completed_on")),
        })

    return columns, data


def get_columns():
    return [
        # Job Details
        {"label": "Job No", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Shp Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Shipping Line", "width": 120},
        {"label": "BL No", "fieldname": "bl_number", "fieldtype": "Data", "width": 120},
        {"label": "Cargo Count", "fieldname": "cargo_count", "fieldtype": "Data", "width": 120},
        {"label": "DnD Start", "fieldname": "dnd_start_date", "fieldtype": "Data", "width": 100},
        {"label": "Stor Start", "fieldname": "storage_start_date", "fieldtype": "Data", "width": 100},
        # Milestones
        {"label": "BL Received Date", "fieldname": "bl_received_date", "fieldtype": "Data", "width": 120},
        {"label": "BL Confirmed Date", "fieldname": "bl_confirmed_date", "fieldtype": "Data", "width": 120},
        {"label": "Vessel Arrived Date", "fieldname": "vessel_arrived_date", "fieldtype": "Data", "width": 120},
        {"label": "SL Invoice Received Date", "fieldname": "sl_invoice_received_date", "fieldtype": "Data", "width": 120},
        {"label": "SL Invoice Payment Date", "fieldname": "sl_invoice_payment_date", "fieldtype": "Data", "width": 120},
        {"label": "Date Discharged from Port", "fieldname": "date_discharged_from_port", "fieldtype": "Data", "width": 120},
        {"label": "DO Requested Date", "fieldname": "do_requested_date", "fieldtype": "Data", "width": 120},
        {"label": "DO Received Date", "fieldname": "do_received_date", "fieldtype": "Data", "width": 120},
        {"label": "Port Release Confirmed Date", "fieldname": "port_release_confirmed_date", "fieldtype": "Data", "width": 120},
        # Status
        {"label": "DnD Days", "fieldname": "total_dnd_days", "fieldtype": "Int", "width": 95},
        {"label": "Stor Days", "fieldname": "total_storage_days", "fieldtype": "Int", "width": 90},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Completed", "fieldname": "completed_on", "fieldtype": "Data", "width": 100},
    ]





