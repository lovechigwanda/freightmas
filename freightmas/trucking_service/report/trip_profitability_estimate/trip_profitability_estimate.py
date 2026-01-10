# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

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
        SELECT name, date_created, customer, truck, route,
               total_estimated_revenue, total_estimated_cost
        FROM `tabTrip`
        WHERE {where_clause}
        ORDER BY date_created DESC
    """.format(where_clause=where_clause), params, as_dict=True)

    for trip in trips:
        est_revenue = flt(trip.total_estimated_revenue)
        est_cost = flt(trip.total_estimated_cost)
        est_profit = est_revenue - est_cost

        # Append raw values without currency formatting
        data.append({
            "name": trip.name,
            "customer": trip.customer,
            "truck": trip.truck,
            "route": trip.route,
            "est_revenue": est_revenue,
            "est_cost": est_cost,
            "est_profit": est_profit
        })

    return columns, data

def get_columns():
    return [
        {"label": "Trip ID", "fieldname": "name", "fieldtype": "Link", "options": "Trip", "width": 130},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 120},
        {"label": "Route", "fieldname": "route", "fieldtype": "Link", "options": "Route", "width": 200},
        {"label": "Est. Revenue", "fieldname": "est_revenue", "fieldtype": "Float", "width": 130},
        {"label": "Est. Cost", "fieldname": "est_cost", "fieldtype": "Float", "width": 130},
        {"label": "Est. Profit", "fieldname": "est_profit", "fieldtype": "Float", "width": 130}
    ]
