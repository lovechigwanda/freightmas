# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import formatdate


def execute(filters=None):
    """Execute the Trip Tracking report."""
    if not filters:
        filters = {}
        
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    """Define columns for the Trip Tracking report."""
    return [
        {
            "label": _("Trip ID"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Trip",
            "width": 130
        },
        {
            "label": _("Truck"),
            "fieldname": "truck",
            "fieldtype": "Link",
            "options": "Truck",
            "width": 100
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 200
        },
        {
            "label": _("Consignee"),
            "fieldname": "consignee",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180
        },
        {
            "label": _("Reference"),
            "fieldname": "customer_reference",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Route"),
            "fieldname": "route",
            "fieldtype": "Link",
            "options": "Route",
            "width": 150
        },
        {
            "label": _("Tracking Remark"),
            "fieldname": "current_milestone_comment",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("Booked On"),
            "fieldname": "booked_on_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Loaded On"),
            "fieldname": "loaded_on_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Border 1 Arrive On"),
            "fieldname": "border_arrived_on",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Border 1 Left On"),
            "fieldname": "border_left_on",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Border 2 Arrive On"),
            "fieldname": "border_2_arrived_on",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Border 2 Left On"),
            "fieldname": "border_2_left_on",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Offloaded On"),
            "fieldname": "offloaded_on_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Empty Return On"),
            "fieldname": "returned_on_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Completed On"),
            "fieldname": "completed_on_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Status"),
            "fieldname": "workflow_state",
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    """Fetch trip data with milestone tracking information."""
    conditions = get_conditions(filters)
    
    data = frappe.db.sql("""
        SELECT 
            name,
            truck,
            customer,
            consignee,
            customer_reference,
            route,
            current_milestone_comment,
            booked_on_date,
            loaded_on_date,
            border_arrived_on,
            border_left_on,
            border_2_arrived_on,
            border_2_left_on,
            offloaded_on_date,
            returned_on_date,
            completed_on_date,
            workflow_state
        FROM `tabTrip`
        WHERE docstatus < 2 {conditions}
        ORDER BY modified DESC
    """.format(conditions=conditions), filters, as_dict=1)
    
    return data


def get_conditions(filters):
    """Build SQL conditions based on filters."""
    conditions = []
    
    if filters.get("from_date"):
        conditions.append("date_created >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("date_created <= %(to_date)s")
    
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
    
    if filters.get("workflow_states"):
        states = filters.get("workflow_states").split(",")
        conditions.append("workflow_state IN %(workflow_states)s")
        filters["workflow_states"] = tuple(states)
        
    return " AND " + " AND ".join(conditions) if conditions else ""
