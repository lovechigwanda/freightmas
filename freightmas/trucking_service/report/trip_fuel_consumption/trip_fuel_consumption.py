# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from freightmas.utils.fuel_utils import calculate_trip_fuel_consumption

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "trip_id",
            "label": _("Trip ID"),
            "fieldtype": "Link",
            "options": "Trip",
            "width": 135
        },
        {
            "fieldname": "truck",
            "label": _("Truck"),
            "fieldtype": "Link",
            "options": "Truck",
            "width": 95
        },
        {
            "fieldname": "route",
            "label": _("Route"),
            "fieldtype": "Link",
            "options": "Route",
            "width": 210
        },
        {
            "fieldname": "total_distance",
            "label": _("Dist(km)"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 90
        },
        {
            "fieldname": "loaded_ratio",
            "label": _("Load (%)"),
            "fieldtype": "Float",
            "precision": 1,
            "width": 95
        },
        {
            "fieldname": "empty_ratio",
            "label": _("Empty (%)"),
            "fieldtype": "Float",
            "precision": 1,
            "width": 95
        },
        {
            "fieldname": "expected_fuel",
            "label": _("Exp(L)"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 90
        },
        {
            "fieldname": "total_fuel",
            "label": _("Act(L)"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 90
        },
        {
            "fieldname": "standard_consumption",
            "label": _("Std km/L"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 90
        },
        {
            "fieldname": "consumption",
            "label": _("Act km/L"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 90
        },
        {
            "fieldname": "fuel_variance",
            "label": _("Variance(L)"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 100
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    trips = frappe.db.sql("""
        SELECT 
            name as trip_id,
            truck,
            route,
            workflow_state
        FROM `tabTrip`
        WHERE docstatus = 1 
        AND {conditions}
        ORDER BY date_created DESC
    """.format(conditions=conditions), filters, as_dict=1)
    
    data = []
    for trip in trips:
        consumption = calculate_trip_fuel_consumption(trip.trip_id)
        if not consumption.get('error'):
            row = {
                **trip,
                **consumption
            }
            data.append(row)
    
    return data

def get_conditions(filters):
    conditions = []
    
    if filters.get("from_date"):
        conditions.append("date_created >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("date_created <= %(to_date)s")
    if filters.get("truck"):
        conditions.append("truck = %(truck)s")
    if filters.get("route"):
        conditions.append("route = %(route)s")
    if filters.get("workflow_state"):
        conditions.append("workflow_state = %(workflow_state)s")
    
    return " AND ".join(conditions) if conditions else "1=1"
