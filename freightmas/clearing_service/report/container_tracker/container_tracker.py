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
    condition = "cj.cargo_type = 'Containerised'"
    if filters.get("customer"):
        condition += f" AND cj.customer = '{filters['customer']}'"
    if filters.get("from_date"):
        condition += f" AND cj.date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        condition += f" AND cj.date_created <= '{filters['to_date']}'"
    if filters.get("job_no"):
        condition += f" AND cj.name = '{filters['job_no']}'"
    if filters.get("bl_number"):
        condition += f" AND cj.bl_number = '{filters['bl_number']}'"

    # Fetch joined data
    rows = frappe.db.sql(f"""
        SELECT
            cj.name AS job_no,
            cj.date_created,
            cj.customer,
            cj.bl_number,
            cj.shipping_line,
            cj.discharge_date,
            cj.dnd_start_date,
            cd.container_number,
            cd.container_type,
            cd.is_loaded,
            cd.gate_out_full_date AS get_out_full_date,
            cd.transporter_name,
            cd.truck_reg_no,
            cd.is_returned,
            cd.gate_in_empty_date AS get_in_empty_date,
            cd.dnd_days_accumulated,
            cd.storage_days_accumulated
        FROM `tabClearing Job` cj
        JOIN `tabContainer Details` cd ON cd.parent = cj.name
        WHERE {condition}
        ORDER BY cj.name, cd.container_number
    """, as_dict=True)

    # Build rows for the report
    for row in rows:
        data.append([
            row.job_no,
            row.date_created,
            row.customer,
            row.bl_number,
            row.shipping_line,
            row.discharge_date,
            row.dnd_start_date,
            row.container_number,
            row.container_type,
            "Yes" if row.is_loaded else "No",
            row.get_out_full_date,
            row.transporter_name,
            row.truck_reg_no,
            "Yes" if row.is_returned else "No",
            row.get_in_empty_date,
            row.dnd_days_accumulated,
            row.storage_days_accumulated
        ])
    return columns, data

def get_columns():
    return [
        {"label": "Job No", "fieldname": "job_no", "fieldtype": "Link", "options": "Clearing Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Date", "width": 95},
        {"label": "Client", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "BL No.", "fieldname": "bl_number", "fieldtype": "Data", "width": 160},
        {"label": "Shipping Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Supplier", "width": 120},
        {"label": "Discharged On", "fieldname": "discharge_date", "fieldtype": "Date", "width": 95},
        {"label": "DnD Starts", "fieldname": "dnd_start_date", "fieldtype": "Date", "width": 95},
        {"label": "Container No.", "fieldname": "container_number", "fieldtype": "Data", "width": 120},
        {"label": "Container Type", "fieldname": "container_type", "fieldtype": "Data", "width": 100},
        {"label": "Is Loaded", "fieldname": "is_loaded", "fieldtype": "Data", "width": 90},
        {"label": "Get Out Date", "fieldname": "get_out_full_date", "fieldtype": "Date", "width": 95},
        {"label": "Transporter", "fieldname": "transporter_name", "fieldtype": "Data", "width": 130},
        {"label": "Truck Reg", "fieldname": "truck_reg_no", "fieldtype": "Data", "width": 95},
        {"label": "Is Returned", "fieldname": "is_returned", "fieldtype": "Data", "width": 90},
        {"label": "Get In Date", "fieldname": "get_in_empty_date", "fieldtype": "Date", "width": 95},
        {"label": "DnD Days", "fieldname": "dnd_days_accumulated", "fieldtype": "Int", "width": 80},
        {"label": "Storage Days", "fieldname": "storage_days_accumulated", "fieldtype": "Int", "width": 90}
    ]
