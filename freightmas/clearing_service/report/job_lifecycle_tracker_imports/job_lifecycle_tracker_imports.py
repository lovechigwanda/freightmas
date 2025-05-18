# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build SQL conditions
    conditions = "cj.direction = 'Import'"
    if filters.get("from_date"):
        conditions += f" AND cj.date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND cj.date_created <= '{filters['to_date']}'"
    if filters.get("customer"):
        conditions += f" AND cj.customer = '{filters['customer']}'"
    if filters.get("job_no"):
        conditions += f" AND cj.name = '{filters['job_no']}'"

    # Fetch data
    rows = frappe.db.sql(f"""
        SELECT
            cj.name AS job_no,
            cj.date_created,
            cj.customer,
            cj.bl_number,
            cj.shipping_line,
            cj.obl_received_date,
            cj.telex_confirmed_date,
            cj.discharge_date,
            cj.container_count,
            cj.sl_invoice_received_date,
            cj.do_received_date,
            cj.sl_invoice_payment_date,
            cj.do_requested_date,
            cj.port_storage_start_date,
            cj.dnd_start_date,
            cj.total_dnd_days,
            cj.total_storage_days
        FROM `tabClearing Job` cj
        WHERE {conditions}
        ORDER BY cj.date_created DESC
    """, as_dict=True)

    for row in rows:
        data.append([
            row.job_no,
            row.date_created,
            row.customer,
            row.bl_number,
            row.shipping_line,
            row.obl_received_date,
            row.telex_confirmed_date,
            row.discharge_date,
            row.container_count,
            row.sl_invoice_received_date,
            row.do_received_date,
            row.sl_invoice_payment_date,
            row.do_requested_date,
            row.port_storage_start_date,
            row.dnd_start_date,
            int(row.total_dnd_days or 0),
            int(row.total_storage_days or 0),
        ])

    return columns, data

def get_columns():
    return [
        {"label": "Job No", "fieldname": "job_no", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Date", "width": 110},
        {"label": "Client", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": "BL No.", "fieldname": "bl_number", "fieldtype": "Data", "width": 140},
        {"label": "Shipping Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": "OBL Received", "fieldname": "obl_received_date", "fieldtype": "Date", "width": 110},
        {"label": "Telex Confirmed", "fieldname": "telex_confirmed_date", "fieldtype": "Date", "width": 110},
        {"label": "Discharged", "fieldname": "discharge_date", "fieldtype": "Date", "width": 110},
        {"label": "Cont Count", "fieldname": "container_count", "fieldtype": "Int", "width": 90},
        {"label": "SL Invoice", "fieldname": "sl_invoice_received_date", "fieldtype": "Date", "width": 110},
        {"label": "D Order", "fieldname": "do_received_date", "fieldtype": "Date", "width": 110},
        {"label": "SL Invoice Paid", "fieldname": "sl_invoice_payment_date", "fieldtype": "Date", "width": 110},
        {"label": "DO Received", "fieldname": "do_requested_date", "fieldtype": "Date", "width": 110},
        {"label": "Storage Starts", "fieldname": "port_storage_start_date", "fieldtype": "Date", "width": 110},
        {"label": "DnD Starts", "fieldname": "dnd_start_date", "fieldtype": "Date", "width": 110},
        {"label": "DnD Days", "fieldname": "total_dnd_days", "fieldtype": "Int", "width": 90},
        {"label": "Storage Days", "fieldname": "total_storage_days", "fieldtype": "Int", "width": 90},
    ]
