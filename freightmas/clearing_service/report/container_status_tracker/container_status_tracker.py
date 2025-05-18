# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime

def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
        {"label": "Job Number", "fieldname": "job_no", "fieldtype": "Data", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Date", "width": 120},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 160},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 140},
        {"label": "Shipping Line", "fieldname": "shipping_line", "fieldtype": "Data", "width": 160},
        {"label": "Container No", "fieldname": "container_number", "fieldtype": "Data", "width": 140},
        {"label": "Cont Type", "fieldname": "container_type", "fieldtype": "Data", "width": 100},
        {"label": "Discharged", "fieldname": "discharge_date", "fieldtype": "Date", "width": 120},
        {"label": "Loaded", "fieldname": "is_loaded", "fieldtype": "Data", "width": 100},
        {"label": "GateOut Date", "fieldname": "gate_out_full_date", "fieldtype": "Date", "width": 120},
        {"label": "Transporter Name", "fieldname": "transporter_name", "fieldtype": "Data", "width": 160},
        {"label": "Returned", "fieldname": "is_returned", "fieldtype": "Data", "width": 100},
        {"label": "GateIn Date", "fieldname": "gate_in_empty_date", "fieldtype": "Date", "width": 120},
        {"label": "DND Days", "fieldname": "dnd_days_accumulated", "fieldtype": "Int", "width": 100},
        {"label": "Sto Days", "fieldname": "storage_days_accumulated", "fieldtype": "Int", "width": 100},
    ]

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

    query = f"""
        SELECT
            cj.name AS job_no,
            cj.date_created,
            cj.customer,
            cj.bl_number,
            cj.shipping_line,
            cd.container_number,
            cd.container_type,
            cj.discharge_date,
            cd.is_loaded,
            cd.gate_out_full_date,
            cd.transporter_name,
            cd.is_returned,
            cd.gate_in_empty_date,
            cd.dnd_days_accumulated,
            cd.storage_days_accumulated
        FROM `tabClearing Job` cj
        JOIN `tabContainer Details` cd ON cd.parent = cj.name
        WHERE {conditions}
        ORDER BY cj.date_created DESC, cj.name, cd.container_number
    """

    rows = frappe.db.sql(query, as_dict=True)

    def format_date(v):
        return v.strftime('%d-%b-%y') if v else ""

    data = []

    is_export = filters.get("is_export")

    for r in rows:
        if is_export:
            data.append([
                r.job_no,
                format_date(r.date_created),
                r.customer,
                r.bl_number,
                r.shipping_line,
                r.container_number,
                r.container_type,
                format_date(r.discharge_date),
                "Yes" if r.is_loaded else "No",
                format_date(r.gate_out_full_date),
                r.transporter_name or "",
                "Yes" if r.is_returned else "No",
                format_date(r.gate_in_empty_date),
                int(r.dnd_days_accumulated or 0),
                int(r.storage_days_accumulated or 0)
            ])
        else:
            data.append([
                r.job_no,
                r.date_created,
                r.customer,
                r.bl_number,
                r.shipping_line,
                r.container_number,
                r.container_type,
                r.discharge_date,
                "Yes" if r.is_loaded else "No",
                r.gate_out_full_date,
                r.transporter_name or "",
                "Yes" if r.is_returned else "No",
                r.gate_in_empty_date,
                int(r.dnd_days_accumulated or 0),
                int(r.storage_days_accumulated or 0)
            ])

    return columns, data
