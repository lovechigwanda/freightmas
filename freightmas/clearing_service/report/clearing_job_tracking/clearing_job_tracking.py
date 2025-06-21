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
        {"label": "Job No", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 150},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 210},
        {"label": "BL No", "fieldname": "bl_number", "fieldtype": "Data", "width": 140},
        {"label": "Cargo Count", "fieldname": "cargo_count", "fieldtype": "Data", "width": 120},
        {"label": "Comment", "fieldname": "current_comment", "fieldtype": "Small Text", "width": 350, "align": "left"},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
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

    jobs = frappe.get_all(
        "Clearing Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "bl_number",
            "cargo_count", "current_comment","status"
        ]
    )

    for job in jobs:
        data.append({
            "name": job["name"],
            "date_created": format_date(job["date_created"]),
            "customer": job["customer"],
            "bl_number": job.get("bl_number", ""),
            "cargo_count": job.get("cargo_count", 0),
            "current_comment": job.get("current_comment", ""),
            "status": job.get("status", ""),
        })

    return columns, data





