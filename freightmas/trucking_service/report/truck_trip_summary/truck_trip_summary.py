# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_simple_data(filters)
    
    for row in data:
        # Ensure revenue is always a numeric value
        if row.get('estimated_revenue'):
            try:
                row['estimated_revenue'] = float(str(row['estimated_revenue']).replace('$', '').replace(',', ''))
            except (ValueError, TypeError):
                row['estimated_revenue'] = 0.0
    
    return columns, data

def get_columns():
    return [
        {"fieldname": "trip_id", "label": _("Trip ID"), "fieldtype": "Link", "options": "Trip", "width": 130},
        {"fieldname": "truck", "label": _("Truck"), "fieldtype": "Link", "options": "Truck", "width": 100},
        {"fieldname": "driver", "label": _("Driver"), "fieldtype": "Data", "width": 170},
        {"fieldname": "route", "label": _("Route"), "fieldtype": "Link", "options": "Route", "width": 170},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
        {"fieldname": "estimated_revenue", "label": _("Revenue"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "date_loaded", "label": _("Load"), "fieldtype": "Data", "width": 100},
        {"fieldname": "date_offloaded", "label": _("Offload"), "fieldtype": "Data", "width": 100},
        {"fieldname": "transit_days", "label": _("Days"), "fieldtype": "Int", "width": 80},
        {"fieldname": "workflow_state", "label": _("Status"), "fieldtype": "Data", "width": 90}
    ]

def get_simple_data(filters):
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

    for row in data:
        # Format dates
        row.date_loaded = frappe.utils.formatdate(row.date_loaded, "dd-MMM-yy")
        row.date_offloaded = frappe.utils.formatdate(row.date_offloaded, "dd-MMM-yy")

        # Format revenue as currency
        row.estimated_revenue = frappe.format_value(row.estimated_revenue, {"fieldtype": "Currency"})

    return data

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
