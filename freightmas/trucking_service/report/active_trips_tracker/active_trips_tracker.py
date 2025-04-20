# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "trip_id", "label": "Trip ID", "fieldtype": "Link", "options": "Trip"},
        {"fieldname": "truck", "label": "Truck", "fieldtype": "Link", "options": "Truck"},
        {"fieldname": "customer", "label": "Customer", "fieldtype": "Link", "options": "Customer"},
        {"fieldname": "route", "label": "Route", "fieldtype": "Data"},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data"},
        {"fieldname": "milestone", "label": "Milestone", "fieldtype": "Data"},
        {"fieldname": "comment", "label": "Comment", "fieldtype": "Text"},
        {"fieldname": "updated_on", "label": "Updated On", "fieldtype": "Datetime"}
    ]

def get_data(filters):
    conditions = []
    params = {"closed": "Closed"}
    
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        params["customer"] = filters["customer"]

    where_clause = "WHERE workflow_state != %(closed)s"
    if conditions:
        where_clause += " AND " + " AND ".join(conditions)

    query = f"""
        SELECT
            name AS trip_id,
            truck,
            customer,
            route,
            workflow_state AS status,
            current_trip_milestone AS milestone,
            current_milestone_comment AS comment,
            updated_on
        FROM tabTrip
        {where_clause}
    """

    return frappe.db.sql(query, params, as_dict=True)