# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from frappe import _
import frappe
from frappe.utils import getdate, nowdate, flt


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Trip ID"),
            "fieldname": "trip_id",
            "fieldtype": "Link",
            "options": "Trip",
            "width": 130,
        },
        {
            "label": _("Route"),
            "fieldname": "route",
            "fieldtype": "Link",
            "options": "Route",
            "width": 200,
        },
        {
            "label": _("Date Loaded"),
            "fieldname": "date_loaded",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Date Offloaded"),
            "fieldname": "date_offloaded",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Standard Transit Time (Days)"),
            "fieldname": "standard_transit_time",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("Actual Transit Time (Days)"),
            "fieldname": "actual_transit_time",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("Variance (Days)"),
            "fieldname": "variance",
            "fieldtype": "Int",
            "width": 100,
            "color": True,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)
    data = []

    trips = frappe.db.sql(
        """
        SELECT 
            t.name as trip_id,
            t.route,
            t.date_loaded,
            t.date_offloaded,
            t.workflow_state as status,
            r.standard_transit_time
        FROM 
            `tabTrip` t
        LEFT JOIN 
            `tabRoute` r ON t.route = r.name
        WHERE
            t.docstatus = 1
            AND t.date_loaded IS NOT NULL
            {conditions}
        ORDER BY 
            t.date_loaded DESC, t.name
    """.format(
            conditions=conditions
        ),
        filters,
        as_dict=1,
    )

    for trip in trips:
        # Calculate actual transit time
        date_loaded = getdate(trip.date_loaded)
        date_offloaded = (
            getdate(trip.date_offloaded) if trip.date_offloaded else getdate(nowdate())
        )
        actual_transit_time = (date_offloaded - date_loaded).days

        # Calculate variance
        standard_transit_time = flt(trip.standard_transit_time) or 0
        variance = actual_transit_time - standard_transit_time

        # Skip if show_variance_only is checked and there's no variance
        if filters.get("show_variance_only") and variance <= 0:
            continue

        row = {
            "trip_id": trip.trip_id,
            "route": trip.route,
            "date_loaded": trip.date_loaded,
            "date_offloaded": trip.date_offloaded,
            "standard_transit_time": standard_transit_time,
            "actual_transit_time": actual_transit_time,
            "variance": variance,
            "status": trip.status,
        }

        data.append(row)

    return data


def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("t.company = %(company)s")

    if filters.get("from_date"):
        conditions.append("t.date_loaded >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("t.date_loaded <= %(to_date)s")

    if filters.get("route"):
        conditions.append("t.route = %(route)s")

    return " AND {}".format(" AND ".join(conditions)) if conditions else ""
