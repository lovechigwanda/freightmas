# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("customer"):
        frappe.throw("Please select a Customer")

    columns = get_columns()
    data = []

    jobs = frappe.db.sql("""
        SELECT name, bl_number, status, current_comment, last_updated_on
        FROM `tabForwarding Job`
        WHERE customer = %(customer)s
              AND status IN ('Draft', 'In Progress', 'Delivered')
              AND docstatus IN (0, 1)
        ORDER BY last_updated_on IS NOT NULL, last_updated_on ASC
    """, {"customer": filters["customer"]}, as_dict=True)

    for job in jobs:
        data.append({
            "job_id": job.name,
            "bl_number": job.get("bl_number") or "",
            "status": job.get("status") or "",
            "tracking_comment": job.get("current_comment") or "",
            "last_updated_on": format_date(job.get("last_updated_on")),
        })

    return columns, data


def get_columns():
    return [
        {"label": "Job ID", "fieldname": "job_id", "fieldtype": "Link", "options": "Forwarding Job", "width": 155},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 165},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Current Tracking Comment", "fieldname": "tracking_comment", "fieldtype": "Data", "width": 380},
        {"label": "Last Updated", "fieldname": "last_updated_on", "fieldtype": "Data", "width": 120},
    ]


def format_date(date_str):
    if date_str:
        try:
            return formatdate(date_str, "dd-MMM-yy")
        except Exception:
            return str(date_str)
    return ""
