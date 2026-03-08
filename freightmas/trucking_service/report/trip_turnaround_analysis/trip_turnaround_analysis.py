# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, date_diff


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_data(filters):
	conditions = ["t.docstatus < 2"]
	params = {}

	if filters.get("from_date"):
		conditions.append("t.date_created >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("t.date_created <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("company"):
		conditions.append("t.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("truck"):
		conditions.append("t.truck = %(truck)s")
		params["truck"] = filters["truck"]

	if filters.get("route"):
		conditions.append("t.route = %(route)s")
		params["route"] = filters["route"]

	where_clause = " AND ".join(conditions)

	# Group by route/truck/customer for averages
	group_by = filters.get("group_by", "Route")

	if group_by == "Truck":
		group_field = "t.truck"
		group_label = "Truck"
	elif group_by == "Customer":
		group_field = "t.customer"
		group_label = "Customer"
	else:
		group_field = "t.route"
		group_label = "Route"

	rows = frappe.db.sql("""
		SELECT
			{group_field} as group_value,
			COUNT(t.name) as trip_count,
			AVG(CASE
				WHEN t.booked_on_date IS NOT NULL AND t.loaded_on_date IS NOT NULL
				THEN DATEDIFF(t.loaded_on_date, t.booked_on_date)
			END) as avg_wait_to_load,
			AVG(CASE
				WHEN t.loaded_on_date IS NOT NULL AND t.offloaded_on_date IS NOT NULL
				THEN DATEDIFF(t.offloaded_on_date, t.loaded_on_date)
			END) as avg_transit,
			AVG(CASE
				WHEN t.offloaded_on_date IS NOT NULL AND t.returned_on_date IS NOT NULL
				THEN DATEDIFF(t.returned_on_date, t.offloaded_on_date)
			END) as avg_return,
			AVG(CASE
				WHEN t.booked_on_date IS NOT NULL AND t.completed_on_date IS NOT NULL
				THEN DATEDIFF(t.completed_on_date, t.booked_on_date)
			END) as avg_total_turnaround
		FROM `tabTrip` t
		WHERE {where_clause}
		GROUP BY {group_field}
		ORDER BY trip_count DESC
	""".format(group_field=group_field, where_clause=where_clause), params, as_dict=True)

	data = []
	for row in rows:
		data.append({
			"group_value": row.group_value,
			"trip_count": row.trip_count,
			"avg_wait_to_load": flt(row.avg_wait_to_load, 1),
			"avg_transit": flt(row.avg_transit, 1),
			"avg_return": flt(row.avg_return, 1),
			"avg_total_turnaround": flt(row.avg_total_turnaround, 1),
		})

	return data


def get_columns():
	return [
		{"label": "Group", "fieldname": "group_value", "fieldtype": "Data", "width": 200},
		{"label": "Trips", "fieldname": "trip_count", "fieldtype": "Int", "width": 70},
		{"label": "Avg Wait-to-Load (days)", "fieldname": "avg_wait_to_load", "fieldtype": "Float", "width": 160},
		{"label": "Avg Transit (days)", "fieldname": "avg_transit", "fieldtype": "Float", "width": 130},
		{"label": "Avg Return (days)", "fieldname": "avg_return", "fieldtype": "Float", "width": 130},
		{"label": "Avg Total Turnaround (days)", "fieldname": "avg_total_turnaround", "fieldtype": "Float", "width": 180},
	]
