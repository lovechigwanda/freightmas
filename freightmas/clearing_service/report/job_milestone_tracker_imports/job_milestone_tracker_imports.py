# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


import frappe
from datetime import datetime

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
            cj.name,
            cj.date_created,
            cj.customer,
            cj.consignee,
            cj.bl_number,
            cj.shipping_line,
            cj.cargo_count,
            cj.bl_received_date,
            cj.bl_confirmed_date,
            cj.discharge_date,
            cj.sl_invoice_received_date,
            cj.sl_invoice_payment_date,
            cj.do_requested_date,
            cj.do_received_date,
            cj.port_storage_start_date,
            cj.dnd_start_date,
            cj.dnd_free_days,
            cj.port_free_days,
            cj.gate_in_empty_date,
            cj.gate_out_full_date,
            cj.to_be_returned
        FROM `tabClearing Job` cj
        WHERE {conditions}
        ORDER BY cj.date_created DESC
    """, as_dict=True)

    today = frappe.utils.nowdate()

    for row in rows:
        # DND Days Calculation
        discharge_date = row.discharge_date or row.date_created
        dnd_free_days = int(row.dnd_free_days or 0)
        port_free_days = int(row.port_free_days or 0)

        # DND end_date logic
        if row.to_be_returned == 1 and row.gate_in_empty_date:
            dnd_end_date = row.gate_in_empty_date
        elif row.to_be_returned == 0 and row.gate_out_full_date:
            dnd_end_date = row.gate_out_full_date
        else:
            dnd_end_date = today

        # Storage end_date logic
        storage_end_date = row.gate_out_full_date or today

        # Calculate DND Days
        dnd_days = calculate_days(discharge_date, dnd_end_date, dnd_free_days)
        # Calculate Storage Days
        storage_days = calculate_days(discharge_date, storage_end_date, port_free_days)

        data.append([
            row.name,
            row.date_created,
            row.customer,
            row.consignee,
            row.bl_number,
            row.shipping_line,
            row.cargo_count,
            row.bl_received_date,
            row.bl_confirmed_date,
            row.discharge_date,
            row.sl_invoice_received_date,
            row.sl_invoice_payment_date,
            row.do_requested_date,
            row.do_received_date,
            row.port_storage_start_date,
            row.dnd_start_date,
            dnd_days,
            storage_days,
        ])

    return columns, data

def calculate_days(start_date, end_date, free_days):
    if not start_date or not end_date:
        return 0
    try:
        start = datetime.strptime(str(start_date), "%Y-%m-%d")
        end = datetime.strptime(str(end_date), "%Y-%m-%d")
        days = (end - start).days + 1 - free_days
        return days if days > 0 else 0
    except Exception:
        return 0

def get_columns():
    return [
        {"label": "Job No", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 110},
        {"label": "Created", "fieldname": "date_created", "fieldtype": "Date", "width": 95},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 130},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Data", "width": 130},
        {"label": "BL No", "fieldname": "bl_number", "fieldtype": "Data", "width": 100},
        {"label": "S Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Supplier", "width": 110},
        {"label": "Cargo Count", "fieldname": "cargo_count", "fieldtype": "Int", "width": 70},
        {"label": "BL Rcvd", "fieldname": "bl_received_date", "fieldtype": "Date", "width": 95},
        {"label": "BL Conf", "fieldname": "bl_confirmed_date", "fieldtype": "Date", "width": 95},
        {"label": "Discharged", "fieldname": "discharge_date", "fieldtype": "Date", "width": 95},
        {"label": "SL Inv Rcvd", "fieldname": "sl_invoice_received_date", "fieldtype": "Date", "width": 95},
        {"label": "SL Inv Paid", "fieldname": "sl_invoice_payment_date", "fieldtype": "Date", "width": 95},
        {"label": "DO Reqsd", "fieldname": "do_requested_date", "fieldtype": "Date", "width": 95},
        {"label": "DO Rcvd Date", "fieldname": "do_received_date", "fieldtype": "Date", "width": 95},
        {"label": "Sto Start", "fieldname": "port_storage_start_date", "fieldtype": "Date", "width": 95},
        {"label": "DND Start", "fieldname": "dnd_start_date", "fieldtype": "Date", "width": 95},
        {"label": "DND Days", "fieldname": "dnd_days", "fieldtype": "Int", "width": 60},
        {"label": "Sto Days", "fieldname": "storage_days", "fieldtype": "Int", "width": 60},
    ]
