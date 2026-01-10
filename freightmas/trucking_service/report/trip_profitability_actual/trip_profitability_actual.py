# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build conditions and parameters for parameterized query
    conditions = ["1=1"]
    params = {}
    
    if filters.get("from_date"):
        conditions.append("date_created >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    
    if filters.get("to_date"):
        conditions.append("date_created <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        params["customer"] = filters["customer"]
    
    if filters.get("truck"):
        conditions.append("truck = %(truck)s")
        params["truck"] = filters["truck"]

    where_clause = " AND ".join(conditions)

    trips = frappe.db.sql("""
        SELECT name, date_created, customer, truck, route
        FROM `tabTrip`
        WHERE {where_clause}
        ORDER BY date_created DESC
    """.format(where_clause=where_clause), params, as_dict=True)

    for trip in trips:
        # Submitted Sales Invoices
        actual_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE trip_reference = %s AND docstatus = 1
        """, trip.name)[0][0] or 0

        # Submitted Purchase Invoices
        actual_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE trip_reference = %s AND docstatus = 1
        """, trip.name)[0][0] or 0

        actual_profit = flt(actual_revenue) - flt(actual_cost)

        # Append raw values without currency formatting
        data.append({
            "name": trip.name,
            "customer": trip.customer,
            "truck": trip.truck,
            "route": trip.route,
            "actual_revenue": actual_revenue,
            "actual_cost": actual_cost,
            "actual_profit": actual_profit
        })

    return columns, data

def get_columns():
    return [
        {"label": "Trip ID", "fieldname": "name", "fieldtype": "Link", "options": "Trip", "width": 130},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 120},
        {"label": "Route", "fieldname": "route", "fieldtype": "Link", "options": "Route", "width": 200},
        {"label": "Actual Revenue", "fieldname": "actual_revenue", "fieldtype": "Float", "width": 130},
        {"label": "Actual Cost", "fieldname": "actual_cost", "fieldtype": "Float", "width": 130},
        {"label": "Actual Profit", "fieldname": "actual_profit", "fieldtype": "Float", "width": 130}
    ]
