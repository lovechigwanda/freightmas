# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe

# trip_tracking_report.py

import frappe

def execute(filters=None):
    columns, data = [], []

    columns = [
        {"label": "Trip Id", "fieldname": "name", "fieldtype": "Link", "options": "Trip", "width": 120},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Date", "width": 100},
        {"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 100},
        {"label": "Driver Name", "fieldname": "driver", "fieldtype": "Link", "options": "Driver", "width": 150},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Customer Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 150},
        {"label": "Route", "fieldname": "route", "fieldtype": "Data", "width": 100},
        {"label": "Trip Direction", "fieldname": "trip_direction", "fieldtype": "Data", "width": 100},
        {"label": "Current Milestone", "fieldname": "current_trip_milestone", "fieldtype": "Data", "width": 150},
        {"label": "Current Milestone Comment", "fieldname": "current_milestone_comment", "fieldtype": "Data", "width": 200},
        {"label": "Updated on", "fieldname": "updated_on", "fieldtype": "Datetime", "width": 120},
    ]

    data = frappe.db.sql("""
        SELECT
            name, date_created, truck, driver, customer, customer_reference, route,
            trip_direction, current_trip_milestone, current_milestone_comment, updated_on
        FROM
            `tabTrip`
        WHERE
            docstatus = 0
    """)

    return columns, data
