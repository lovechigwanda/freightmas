# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, getdate, add_days


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    conditions = "1=1"
    if filters.get("from_date"):
        conditions += f" AND date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND date_created <= '{filters['to_date']}'"
    if filters.get("customer"):
        conditions += f" AND customer = '{filters['customer']}'"

    jobs = frappe.db.sql(f"""
        SELECT name, date_created, customer, customer_reference, 
               direction, shipment_mode, eta, ata,
               status, current_comment
        FROM `tabForwarding Job`
        WHERE {conditions}
        ORDER BY date_created DESC
    """, as_dict=True)

    # Filter jobs based on completed status and date (show current jobs + recently completed within 5 days)
    today = getdate()
    five_days_ago = add_days(today, -5)
    
    filtered_jobs = []
    for job in jobs:
        # Include if not completed
        if job.get("status") != "Completed":
            filtered_jobs.append(job)
        # Or if completed within last 5 days
        elif job.get("completed_on"):
            completed_date = getdate(job.get("completed_on"))
            if completed_date >= five_days_ago:
                filtered_jobs.append(job)

    for job in filtered_jobs:
        # Combine direction and shipment mode
        direction_shipment = ""
        if job.get("direction") and job.get("shipment_mode"):
            direction_shipment = f"{job.get('shipment_mode')} {job.get('direction')}"
        elif job.get("direction"):
            direction_shipment = job.get("direction")
        elif job.get("shipment_mode"):
            direction_shipment = job.get("shipment_mode")

        data.append({
            "name": job.name,
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "direction": direction_shipment,
            "customer_reference": job.get("customer_reference", ""),
            "eta": format_date(job.get("eta")),
            "ata": format_date(job.get("ata")),
            "status": job.get("status", ""),
            "current_comment": job.get("current_comment", ""),
        })

    return columns, data


def get_columns():
    return [
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 120},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 140},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 100},
        {"label": "ATA", "fieldname": "ata", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": "Current Comment", "fieldname": "current_comment", "fieldtype": "Data", "width": 250},
    ]


def format_date(date_str):
    """Format date string to dd-MMM-yy format."""
    if not date_str:
        return ""
    try:
        return formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str
