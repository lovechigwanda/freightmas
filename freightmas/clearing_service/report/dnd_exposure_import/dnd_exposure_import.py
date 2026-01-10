# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime, timedelta

def format_ddmmmyy(date_val):
    if not date_val:
        return ""
    try:
        # Accepts both date and string input
        if isinstance(date_val, str):
            dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
        else:
            dt = date_val
        return dt.strftime("%d-%b-%y")
    except Exception:
        return date_val  # fallback, just in case

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build SQL conditions for parent
    conditions = ["cj.direction = 'Import'"]
    params = {}
    
    if filters.get("from_date"):
        conditions.append("cj.date_created >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("cj.date_created <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    if filters.get("customer"):
        conditions.append("cj.customer = %(customer)s")
        params["customer"] = filters["customer"]
    if filters.get("job_no"):
        conditions.append("cj.name = %(job_no)s")
        params["job_no"] = filters["job_no"]

    where_clause = " AND ".join(conditions)

    # Fetch parent jobs
    jobs = frappe.db.sql("""
        SELECT
            cj.name,
            cj.date_created,
            cj.customer,
            cj.consignee,
            cj.bl_number,
            cj.shipping_line,
            cj.cargo_count,
            cj.dnd_free_days,
            cj.port_free_days,
            cj.dnd_start_date,
            cj.storage_start_date,
            cj.discharge_date
        FROM `tabClearing Job` cj
        WHERE {where_clause}
        ORDER BY cj.date_created DESC
    """.format(where_clause=where_clause), params, as_dict=True)

    today = frappe.utils.nowdate()

    for job in jobs:
        discharge_date = job.discharge_date

        # If discharge_date is not set, DND and Storage calculations are skipped
        if not discharge_date:
            dnd_start_date = None
            storage_start_date = None
            dnd_days_total = 0
            storage_days_total = 0
        else:
            dnd_start_date = job.dnd_start_date
            storage_start_date = job.storage_start_date

            dnd_free_days = int(job.dnd_free_days or 0)
            port_free_days = int(job.port_free_days or 0)

            # Fetch child rows for this job
            children = frappe.db.sql("""
                SELECT
                    gate_in_empty_date,
                    gate_out_full_date,
                    to_be_returned
                FROM `tabCargo Package Details`
                WHERE parent = %s
            """, (job.name,), as_dict=True)

            dnd_days_total = 0
            storage_days_total = 0

            if children:
                for child in children:
                    to_be_returned = frappe.utils.cint(child.to_be_returned)

                    # DND end_date logic
                    if to_be_returned == 1 and child.gate_in_empty_date:
                        dnd_end_date = child.gate_in_empty_date
                    elif to_be_returned == 0 and child.gate_out_full_date:
                        dnd_end_date = child.gate_out_full_date
                    else:
                        dnd_end_date = today

                    # Storage end_date logic
                    storage_end_date = child.gate_out_full_date or today

                    # Calculate DND Days
                    dnd_days = calculate_days(discharge_date, dnd_end_date, dnd_free_days)
                    # Calculate Storage Days
                    storage_days = calculate_days(discharge_date, storage_end_date, port_free_days)

                    dnd_days_total += dnd_days
                    storage_days_total += storage_days
            else:
                # No child rows: use today's date as end date for both
                dnd_days_total = calculate_days(discharge_date, today, dnd_free_days)
                storage_days_total = calculate_days(discharge_date, today, port_free_days)

        data.append([
            job.name,
            format_ddmmmyy(job.date_created),
            job.customer,
            job.consignee,
            job.bl_number,
            job.shipping_line,
            job.cargo_count,
            format_ddmmmyy(dnd_start_date),      # Use stored DND Start Date
            format_ddmmmyy(storage_start_date),  # Use stored Storage Start Date
            dnd_days_total,
            storage_days_total,
        ])

    return columns, data

def calculate_days(start_date, end_date, free_days):
    if not start_date or not end_date:
        return 0
    try:
        start = datetime.strptime(str(start_date)[:10], "%Y-%m-%d")
        end = datetime.strptime(str(end_date)[:10], "%Y-%m-%d")
        days = (end - start).days - int(free_days or 0)
        return days if days > 0 else 0
    except Exception:
        return 0

def get_columns():
    return [
        {"label": "Job No", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 110},
        {"label": "Created", "fieldname": "date_created", "fieldtype": "Data", "width": 95},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 130},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Data", "width": 130},
        {"label": "BL No", "fieldname": "bl_number", "fieldtype": "Data", "width": 100},
        {"label": "S Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Supplier", "width": 110},
        {"label": "Cargo Count", "fieldname": "cargo_count", "fieldtype": "Int", "width": 70},
        {"label": "DND Start", "fieldname": "dnd_start_date", "fieldtype": "Data", "width": 95},
        {"label": "Sto Start", "fieldname": "storage_start_date", "fieldtype": "Data", "width": 95},
        {"label": "DND Days", "fieldname": "dnd_days", "fieldtype": "Int", "width": 60},
        {"label": "Sto Days", "fieldname": "storage_days", "fieldtype": "Int", "width": 60},
    ]
