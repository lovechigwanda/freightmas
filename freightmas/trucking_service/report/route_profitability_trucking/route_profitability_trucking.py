# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


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

	if filters.get("route"):
		conditions.append("t.route = %(route)s")
		params["route"] = filters["route"]

	where_clause = " AND ".join(conditions)

	routes = frappe.db.sql("""
		SELECT
			t.route,
			COUNT(t.name) as trip_count,
			SUM(IFNULL(t.total_estimated_revenue, 0)) as total_revenue,
			SUM(IFNULL(t.total_estimated_cost, 0)) as total_est_cost,
			AVG(CASE
				WHEN t.date_offloaded IS NOT NULL AND t.date_loaded IS NOT NULL
				THEN DATEDIFF(t.date_offloaded, t.date_loaded)
			END) as avg_transit_days,
			SUM(IFNULL(t.distance_loaded, 0) + IFNULL(t.extra_distance_loaded, 0)
				+ IFNULL(t.distance_empty, 0) + IFNULL(t.extra_distance_empty, 0)) as total_km
		FROM `tabTrip` t
		WHERE {where_clause}
		GROUP BY t.route
		ORDER BY total_revenue DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	# Fuel costs per route
	fuel_map = {}
	fuel_rows = frappe.db.sql("""
		SELECT t.route, SUM(IFNULL(fa.amount, 0)) as fuel_cost
		FROM `tabTrip Fuel Allocation` fa
		INNER JOIN `tabTrip` t ON fa.parent = t.name
		WHERE {where_clause}
		GROUP BY t.route
	""".format(where_clause=where_clause), params, as_dict=True)
	for r in fuel_rows:
		fuel_map[r.route] = flt(r.fuel_cost)

	# Other costs per route
	other_map = {}
	cost_rows = frappe.db.sql("""
		SELECT t.route, SUM(IFNULL(oc.total_amount, 0)) as other_cost
		FROM `tabTrip Other Costs` oc
		INNER JOIN `tabTrip` t ON oc.parent = t.name
		WHERE {where_clause}
		GROUP BY t.route
	""".format(where_clause=where_clause), params, as_dict=True)
	for r in cost_rows:
		other_map[r.route] = flt(r.other_cost)

	data = []
	for row in routes:
		revenue = flt(row.total_revenue)
		fuel = fuel_map.get(row.route, 0)
		other = other_map.get(row.route, 0)
		total_cost = flt(fuel) + flt(other)
		profit = revenue - total_cost
		margin_pct = (profit / revenue * 100) if revenue else 0
		avg_rev = (revenue / row.trip_count) if row.trip_count else 0
		avg_profit = (profit / row.trip_count) if row.trip_count else 0

		data.append({
			"route": row.route,
			"trip_count": row.trip_count,
			"total_revenue": flt(revenue, 2),
			"total_cost": flt(total_cost, 2),
			"total_profit": flt(profit, 2),
			"margin_percent": flt(margin_pct, 1),
			"avg_revenue_per_trip": flt(avg_rev, 2),
			"avg_profit_per_trip": flt(avg_profit, 2),
			"avg_transit_days": flt(row.avg_transit_days, 1),
			"total_km": flt(row.total_km, 0),
		})

	return data


def get_columns():
	return [
		{"label": "Route", "fieldname": "route", "fieldtype": "Link", "options": "Route", "width": 200},
		{"label": "Trips", "fieldname": "trip_count", "fieldtype": "Int", "width": 70},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 120},
		{"label": "Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 120},
		{"label": "Profit", "fieldname": "total_profit", "fieldtype": "Currency", "width": 120},
		{"label": "Margin %", "fieldname": "margin_percent", "fieldtype": "Percent", "width": 90},
		{"label": "Avg Rev/Trip", "fieldname": "avg_revenue_per_trip", "fieldtype": "Currency", "width": 120},
		{"label": "Avg Profit/Trip", "fieldname": "avg_profit_per_trip", "fieldtype": "Currency", "width": 120},
		{"label": "Avg Transit Days", "fieldname": "avg_transit_days", "fieldtype": "Float", "width": 110},
		{"label": "Total Km", "fieldname": "total_km", "fieldtype": "Float", "width": 90},
	]
