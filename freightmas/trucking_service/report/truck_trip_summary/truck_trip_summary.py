# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, fmt_money

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "truck", "label": _("Truck"), "fieldtype": "Link", "options": "Truck", "width": 130},
        {"fieldname": "driver", "label": _("Driver"), "fieldtype": "Data", "width": 150},
        {"fieldname": "trip_id", "label": _("Trip ID"), "fieldtype": "Link", "options": "Trip", "width": 100},
        {"fieldname": "route", "label": _("Route"), "fieldtype": "Link", "options": "Route", "width": 170},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
        {"fieldname": "estimated_revenue", "label": _("Revenue"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "date_loaded", "label": _("Load"), "fieldtype": "Data", "width": 100},
        {"fieldname": "date_offloaded", "label": _("Offload"), "fieldtype": "Data", "width": 100},
        {"fieldname": "transit_days", "label": _("Days"), "fieldtype": "Int", "width": 80},
        {"fieldname": "workflow_state", "label": _("Status"), "fieldtype": "Data", "width": 90}
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    data = frappe.db.sql(f"""
        SELECT 
            t.truck, t.driver, t.name AS trip_id, t.route,
            t.customer,
            IFNULL(t.total_estimated_revenue, 0) AS estimated_revenue,
            t.date_loaded, t.date_offloaded,
            CASE
                WHEN t.date_offloaded IS NOT NULL THEN DATEDIFF(t.date_offloaded, t.date_loaded)
                ELSE DATEDIFF(CURDATE(), t.date_loaded)
            END AS transit_days,
            t.workflow_state
        FROM `tabTrip` t
        WHERE t.docstatus < 2 {conditions}
        ORDER BY t.truck, t.date_loaded DESC
    """, filters, as_dict=True)

    result = []
    current_truck = None
    truck_total = 0
    truck_trips = 0

    for row in data:
        # Format dates
        row.date_loaded = frappe.utils.formatdate(row.date_loaded, "dd-MMM-yy")
        row.date_offloaded = frappe.utils.formatdate(row.date_offloaded, "dd-MMM-yy")

        if row.truck != current_truck:
            if current_truck:
                # Add total row for Excel/PDF export formatting
                result.append({
                    "truck": "",
                    "driver": "",
                    "trip_id": "",
                    "route": "Total for " + current_truck,
                    "customer": f"Total Trips: {truck_trips}",
                    "estimated_revenue": truck_total,
                    "is_total": 1,
                    "bold": 1  # Add bold flag for export formats
                })
                result.append({})
            
            current_truck = row.truck
            truck_total = 0
            truck_trips = 0

        result.append(row)
        truck_total += flt(row.estimated_revenue)
        truck_trips += 1

    if current_truck:
        # Add final total row
        result.append({
            "truck": "",
            "driver": "",
            "trip_id": "",
            "route": "Total for " + current_truck,
            "customer": f"Trip(s): {truck_trips}",
            "estimated_revenue": truck_total,
            "is_total": 1,
            "bold": 1  # Add bold flag for export formats
        })

    return result

def get_conditions(filters):
    conditions = []
    if filters.get("company"):
        conditions.append("t.company = %(company)s")
    if filters.get("truck"):
        conditions.append("t.truck = %(truck)s")
    if filters.get("customer"):
        conditions.append("t.customer = %(customer)s")
    if filters.get("direction"):
        conditions.append("t.trip_direction = %(direction)s")
    if filters.get("from_date"):
        conditions.append("t.date_created >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("t.date_created <= %(to_date)s")

    return " AND " + " AND ".join(conditions) if conditions else ""
