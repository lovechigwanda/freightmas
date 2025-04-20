# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


import frappe

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {"label": "Trip ID", "fieldname": "name", "fieldtype": "Link", "options": "Trip", "width": 120},
        {"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 120},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Status", "fieldname": "workflow_state", "fieldtype": "Data", "width": 100},
        {"label": "Current Milestone", "fieldname": "current_trip_milestone", "fieldtype": "Data", "width": 150},
        {"label": "Milestone Comment", "fieldname": "current_milestone_comment", "fieldtype": "Data", "width": 200},
        {"label": "Last Updated", "fieldname": "updated_on", "fieldtype": "Date", "width": 120}
    ]

def get_data(filters):
    conditions = "WHERE workflow_state != 'Closed'"
    filter_values = {}
    
    if filters.get("customer"):
        conditions += " AND customer = %(customer)s"
        filter_values["customer"] = filters["customer"]
    
    query = f"""
        SELECT name, truck, customer, workflow_state, current_trip_milestone,
               current_milestone_comment, updated_on
        FROM `tabTrip`
        {conditions}
        ORDER BY updated_on DESC
    """
    
    return frappe.db.sql(query, filter_values, as_dict=True)
