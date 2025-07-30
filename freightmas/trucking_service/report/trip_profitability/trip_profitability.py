# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    conditions = "1=1"
    if filters.get("from_date"):
        conditions += f" AND date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND date_created <= '{filters['to_date']}'"
    if filters.get("customer"):
        conditions += f" AND customer = '{filters['customer']}'"
    if filters.get("truck"):
        conditions += f" AND truck = '{filters['truck']}'"

    trips = frappe.db.sql(f"""
        SELECT name, date_created, customer, truck, route,
               total_estimated_revenue, total_estimated_cost
        FROM `tabTrip`
        WHERE {conditions}
        ORDER BY date_created DESC
    """, as_dict=True)

    for trip in trips:
        est_revenue = flt(trip.total_estimated_revenue)
        est_cost = flt(trip.total_estimated_cost)
        est_profit = est_revenue - est_cost

        draft_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE trip_reference = %s AND docstatus = 0
        """, trip.name)[0][0] or 0

        draft_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE trip_reference = %s AND docstatus = 0
        """, trip.name)[0][0] or 0

        draft_profit = flt(draft_revenue) - flt(draft_cost)

        actual_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE trip_reference = %s AND docstatus = 1
        """, trip.name)[0][0] or 0

        actual_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE trip_reference = %s AND docstatus = 1
        """, trip.name)[0][0] or 0

        actual_profit = flt(actual_revenue) - flt(actual_cost)

        # Format currency fields
        data.append({
            "name": trip.name,
            "customer": trip.customer,
            "truck": trip.truck,
            "route": trip.route,
            "est_revenue": frappe.format_value(est_revenue, {"fieldtype": "Currency"}),
            "est_cost": frappe.format_value(est_cost, {"fieldtype": "Currency"}),
            "est_profit": frappe.format_value(est_profit, {"fieldtype": "Currency"}),
            "draft_revenue": frappe.format_value(draft_revenue, {"fieldtype": "Currency"}),
            "draft_cost": frappe.format_value(draft_cost, {"fieldtype": "Currency"}),
            "draft_profit": frappe.format_value(draft_profit, {"fieldtype": "Currency"}),
            "actual_revenue": frappe.format_value(actual_revenue, {"fieldtype": "Currency"}),
            "actual_cost": frappe.format_value(actual_cost, {"fieldtype": "Currency"}),
            "actual_profit": frappe.format_value(actual_profit, {"fieldtype": "Currency"})
        })

    return columns, data

def get_columns():
    return [
        {"label": "Trip ID", "fieldname": "name", "fieldtype": "Link", "options": "Trip", "width": 130},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 100},
        {"label": "Route", "fieldname": "route", "fieldtype": "Link", "options": "Route", "width": 180},
        {"label": "Est. Revenue", "fieldname": "est_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Cost", "fieldname": "est_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Profit", "fieldname": "est_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Draft Revenue", "fieldname": "draft_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Draft Cost", "fieldname": "draft_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Draft Profit", "fieldname": "draft_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Actual Revenue", "fieldname": "actual_revenue", "fieldtype": "Currency", "width": 130},
        {"label": "Actual Cost", "fieldname": "actual_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Actual Profit", "fieldname": "actual_profit", "fieldtype": "Currency", "width": 120}
    ]
