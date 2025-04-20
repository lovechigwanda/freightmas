# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe

import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "name", "label": "Trip ID", "fieldtype": "Data", "width": 120},
        {"fieldname": "truck", "label": "Truck", "fieldtype": "Link", "options": "Vehicle", "width": 120},
        {"fieldname": "customer", "label": "Customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"fieldname": "route", "label": "Route", "fieldtype": "Link", "options": "Route", "width": 150},
        {"fieldname": "workflow_state", "label": "Status", "fieldtype": "Data", "width": 120},
        {"fieldname": "current_trip_milestone", "label": "Milestone", "fieldtype": "Data", "width": 180},
        {"fieldname": "current_milestone_comment", "label": "Comment", "fieldtype": "Data", "width": 250},
        {"fieldname": "updated_on", "label": "Updated On", "fieldtype": "Datetime", "width": 150}
    ]

    # Ensure customer filter is applied
    customer = filters.get("customer") if filters else None
    if not customer:
        return columns, []

    data = frappe.db.sql(
        """
        SELECT
            name, truck, customer, route, workflow_state,
            current_trip_milestone, current_milestone_comment, updated_on
        FROM `tabTrip`
        WHERE workflow_state NOT IN ('Closed')
        AND customer = %s
        """, (customer,), as_dict=True
    )

    return columns, data
