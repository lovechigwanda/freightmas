# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Driver ID"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Driver",
            "width": 180
        },
        {
            "label": _("Full Name"),
            "fieldname": "full_name",
            "fieldtype": "Data",
            "width": 220
        },
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150
        },
        {
            "label": _("License Number"),
            "fieldname": "license_number",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Passport Number"),
            "fieldname": "passport_number",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Truck Linked"),
            "fieldname": "truck_linked",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Truck"),
            "fieldname": "truck_id",
            "fieldtype": "Link",
            "options": "Truck",
            "width": 120
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Get all drivers with their details
    driver_data = frappe.db.sql(f"""
        SELECT 
            d.name,
            d.full_name,
            d.employee,
            d.license_number,
            d.passport_number,
            CASE 
                WHEN t.name IS NOT NULL THEN 'Yes'
                ELSE 'No'
            END as truck_linked,
            t.name as truck_id,
            d.status
        FROM 
            `tabDriver` d
        LEFT JOIN 
            `tabTruck` t ON d.name = t.assigned_driver
        {conditions}
        ORDER BY 
            d.status DESC, d.full_name
    """, as_dict=1)
    
    return driver_data

def get_conditions(filters):
    conditions = "WHERE 1=1"
    
    if filters.get("status"):
        conditions += f" AND d.status = '{filters.get('status')}'"
    
    if filters.get("truck_linked"):
        if filters.get("truck_linked") == "Yes":
            conditions += " AND t.name IS NOT NULL"
        else:
            conditions += " AND t.name IS NULL"
    
    if filters.get("from_date"):
        conditions += f" AND d.creation >= '{filters.get('from_date')}'"
    
    if filters.get("to_date"):
        conditions += f" AND d.creation <= '{filters.get('to_date')}'"
    
    return conditions



