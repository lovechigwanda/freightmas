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

	if filters.get("driver"):
		conditions.append("t.driver = %(driver)s")
		params["driver"] = filters["driver"]

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql("""
		SELECT
			t.driver,
			COUNT(t.name) as trip_count,
			SUM(IFNULL(t.total_estimated_revenue, 0)) as total_revenue,
			SUM(IFNULL(t.distance_loaded, 0) + IFNULL(t.extra_distance_loaded, 0)
				+ IFNULL(t.distance_empty, 0) + IFNULL(t.extra_distance_empty, 0)) as total_km,
			AVG(CASE
				WHEN t.date_offloaded IS NOT NULL AND t.date_loaded IS NOT NULL
				THEN DATEDIFF(t.date_offloaded, t.date_loaded)
			END) as avg_transit_days,
			COUNT(CASE WHEN t.is_completed = 1 THEN 1 END) as completed_trips
		FROM `tabTrip` t
		WHERE {where_clause} AND t.driver IS NOT NULL AND t.driver != ''
		GROUP BY t.driver
		ORDER BY total_revenue DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	# Fuel consumption per driver
	fuel_map = {}
	fuel_rows = frappe.db.sql("""
		SELECT t.driver, SUM(IFNULL(fa.qty, 0)) as fuel_litres, SUM(IFNULL(fa.amount, 0)) as fuel_cost
		FROM `tabTrip Fuel Allocation` fa
		INNER JOIN `tabTrip` t ON fa.parent = t.name
		WHERE {where_clause} AND t.driver IS NOT NULL AND t.driver != ''
		GROUP BY t.driver
	""".format(where_clause=where_clause), params, as_dict=True)
	for r in fuel_rows:
		fuel_map[r.driver] = {"litres": flt(r.fuel_litres), "cost": flt(r.fuel_cost)}

	data = []
	for row in rows:
		revenue = flt(row.total_revenue)
		total_km = flt(row.total_km)
		fuel_info = fuel_map.get(row.driver, {"litres": 0, "cost": 0})
		km_per_litre = (total_km / fuel_info["litres"]) if fuel_info["litres"] else 0
		avg_rev_per_trip = (revenue / row.trip_count) if row.trip_count else 0

		data.append({
			"driver": row.driver,
			"trip_count": row.trip_count,
			"completed_trips": row.completed_trips,
			"total_revenue": flt(revenue, 2),
			"total_km": flt(total_km, 0),
			"fuel_litres": flt(fuel_info["litres"], 2),
			"fuel_cost": flt(fuel_info["cost"], 2),
			"km_per_litre": flt(km_per_litre, 2),
			"avg_transit_days": flt(row.avg_transit_days, 1),
			"avg_revenue_per_trip": flt(avg_rev_per_trip, 2),
		})

	return data


def get_columns():
	return [
		{"label": "Driver", "fieldname": "driver", "fieldtype": "Data", "width": 170},
		{"label": "Trips", "fieldname": "trip_count", "fieldtype": "Int", "width": 70},
		{"label": "Completed", "fieldname": "completed_trips", "fieldtype": "Int", "width": 90},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 120},
		{"label": "Total Km", "fieldname": "total_km", "fieldtype": "Float", "width": 90},
		{"label": "Fuel (L)", "fieldname": "fuel_litres", "fieldtype": "Float", "width": 90},
		{"label": "Fuel Cost", "fieldname": "fuel_cost", "fieldtype": "Currency", "width": 110},
		{"label": "Km/L", "fieldname": "km_per_litre", "fieldtype": "Float", "width": 80},
		{"label": "Avg Transit Days", "fieldname": "avg_transit_days", "fieldtype": "Float", "width": 110},
		{"label": "Avg Rev/Trip", "fieldname": "avg_revenue_per_trip", "fieldtype": "Currency", "width": 120},
	]
