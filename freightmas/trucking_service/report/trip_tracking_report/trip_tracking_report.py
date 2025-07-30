# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
    if not filters:
        filters = {}
        
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {
            "label": "Trip ID",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Trip",
            "width": 130
        },
        {
            "label": "Created",
            "fieldname": "date_created",
            "fieldtype": "Data",
            "width": 90
        },
        {
            "label": "Truck",
            "fieldname": "truck",
            "fieldtype": "Link",
            "options": "Truck",
            "width": 100
        },
        {
            "label": "Customer",
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 210
        },
        {
            "label": "Loaded",
            "fieldname": "date_loaded",
            "fieldtype": "Data",
            "width": 90
        },
        {
            "label": "Status",
            "fieldname": "workflow_state",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": "Tracking Comment",
            "fieldname": "current_milestone_comment",
            "fieldtype": "Data",
            "width": 370,
            "align": "left"  # Add alignment property
        },
        {
            "label": "Updated",
            "fieldname": "modified",
            "fieldtype": "Data",
            "width": 100
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    data = frappe.db.sql("""
        SELECT 
            name,
            date_created,
            truck,
            customer,
            date_loaded,
            workflow_state,
            current_milestone_comment,
            modified
        FROM `tabTrip`
        WHERE docstatus < 2 %s
        ORDER BY modified DESC
    """ % conditions, filters, as_dict=1)
    
    # Format dates
    for row in data:
        row.date_created = formatdate(row.date_created, "dd-MMM-yy")
        row.date_loaded = formatdate(row.date_loaded, "dd-MMM-yy")
        row.modified = formatdate(row.modified, "dd-MMM-yy")
    
    return data

def get_conditions(filters):
    conditions = []
    
    if filters.get("from_date"):
        conditions.append("date_created >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("date_created <= %(to_date)s")
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
    if filters.get("workflow_states"):
        states = filters.get("workflow_states").split(",")
        conditions.append("workflow_state IN %(workflow_states)s")
        filters["workflow_states"] = tuple(states)
        
    return " AND " + " AND ".join(conditions) if conditions else ""
