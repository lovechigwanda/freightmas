# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Truck ID"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Truck",
            "width": 100,
        },
        {
            "label": _("Horse"),
            "fieldname": "horse",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Trailer"),
            "fieldname": "trailer",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Driver"),
            "fieldname": "assigned_driver_name",
            "fieldtype": "Data",
            "width": 215,
        },
        {
            "label": _("Fuel Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 170,
        },
        {
            "label": _("Cost Centre"),
            "fieldname": "cost_centre",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 150,
        },
        {
            "label": _("Load(km/L)"),
            "fieldname": "loaded_fuel_consumption",
            "fieldtype": "Float",
            "precision": 2,
            "width": 115,
        },
        {
            "label": _("Empty (km/L)"),
            "fieldname": "empty_fuel_consumption",
            "fieldtype": "Float",
            "precision": 2,
            "width": 115,
        },
        {
            "label": _("Status"),
            "fieldname": "truck_status",
            "fieldtype": "Data",
            "width": 120,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    return frappe.db.sql(
        f"""
        SELECT 
            name,
            horse,
            assigned_trailer as trailer,  # Changed from trailer to assigned_trailer
            assigned_driver_name,
            warehouse,
            cost_centre,
            loaded_fuel_consumption,
            empty_fuel_consumption,
            truck_status
        FROM `tabTruck`
        WHERE 1=1
        {conditions}
        ORDER BY name
    """,
        filters,
        as_dict=1,
    )


def get_conditions(filters):
    conditions = []

    if filters.get("truck_status"):
        conditions.append("AND truck_status = %(truck_status)s")

    if filters.get("driver_linked"):
        if filters.get("driver_linked") == "Yes":
            conditions.append("AND assigned_driver IS NOT NULL")
        else:
            conditions.append("AND assigned_driver IS NULL")

    return " ".join(conditions)
