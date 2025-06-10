# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime

def format_ddmmmyy(date_val):
    if not date_val:
        return ""
    try:
        if isinstance(date_val, str):
            dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
        else:
            dt = date_val
        return dt.strftime("%d-%b-%y")
    except Exception:
        return date_val

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

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build conditions based on filters
    conditions = "cj.direction = 'Import'"
    if filters.get("from_date"):
        conditions += f" AND cj.date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND cj.date_created <= '{filters['to_date']}'"
    if filters.get("customer"):
        conditions += f" AND cj.customer = '{filters['customer']}'"
    if filters.get("job_no"):
        conditions += f" AND cj.name = '{filters['job_no']}'"
    if filters.get("bl_number"):
        conditions += f" AND cj.bl_number = '{filters['bl_number']}'"
    if filters.get("job_status"):
        conditions += f" AND cj.status = '{filters['job_status']}'"

    jobs = frappe.db.sql(f"""
        SELECT
            cj.name, cj.date_created, cj.customer, cj.consignee, cj.bl_number,
            cj.shipping_line, cj.discharge_date, cj.dnd_free_days, cj.port_free_days,
            cj.dnd_start_date, cj.storage_start_date
        FROM `tabClearing Job` cj
        WHERE {conditions}
        ORDER BY cj.date_created DESC
    """, as_dict=True)

    today = frappe.utils.nowdate()

    for job in jobs:
        if not job.discharge_date:
            continue

        containers = frappe.db.sql("""
            SELECT
                is_loaded, gate_out_full_date,
                is_returned, gate_in_empty_date
            FROM `tabCargo Package Details`
            WHERE parent = %s
        """, (job.name,), as_dict=True)

        total_dnd_days = 0
        total_sto_days = 0

        for cont in containers:
            # DND End Date Logic
            if frappe.utils.cint(cont.is_returned) == 1 and cont.gate_in_empty_date:
                dnd_end_date = cont.gate_in_empty_date
            elif frappe.utils.cint(cont.is_returned) == 0 and cont.gate_out_full_date:
                dnd_end_date = cont.gate_out_full_date
            else:
                dnd_end_date = today

            # Storage End Date Logic
            storage_end_date = cont.gate_out_full_date or today

            total_dnd_days += calculate_days(job.discharge_date, dnd_end_date, job.dnd_free_days)
            total_sto_days += calculate_days(job.discharge_date, storage_end_date, job.port_free_days)

        data.append([
            job.name,
            format_ddmmmyy(job.date_created),
            job.customer,
            job.consignee,
            job.bl_number,
            job.shipping_line,
            format_ddmmmyy(job.discharge_date),
            format_ddmmmyy(job.dnd_start_date),      # Use stored DND Start Date
            format_ddmmmyy(job.storage_start_date),  # Use stored Storage Start Date
            total_dnd_days,
            total_sto_days,
        ])

    return columns, data

def get_columns():
    return [
        {"label": "Job No", "fieldname": "job_no", "fieldtype": "Link", "options": "Clearing Job", "width": 110},
        {"label": "Job Date", "fieldname": "job_date", "fieldtype": "Data", "width": 95},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Data", "width": 120},
        {"label": "BL No", "fieldname": "bl_number", "fieldtype": "Data", "width": 110},
        {"label": "S. Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Supplier", "width": 110},
        {"label": "Discharge", "fieldname": "discharge_date", "fieldtype": "Data", "width": 90},
        {"label": "DND Start", "fieldname": "dnd_start", "fieldtype": "Data", "width": 90},
        {"label": "Sto Start", "fieldname": "sto_start", "fieldtype": "Data", "width": 90},
        {"label": "DND Days", "fieldname": "dnd_days", "fieldtype": "Int", "width": 80},
        {"label": "Sto Days", "fieldname": "sto_days", "fieldtype": "Int", "width": 80},
    ]
