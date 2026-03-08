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

	if filters.get("truck"):
		conditions.append("t.truck = %(truck)s")
		params["truck"] = filters["truck"]

	if filters.get("company"):
		conditions.append("t.company = %(company)s")
		params["company"] = filters["company"]

	where_clause = " AND ".join(conditions)

	trucks = frappe.db.sql("""
		SELECT
			t.truck,
			COUNT(t.name) as trip_count,
			SUM(IFNULL(t.total_estimated_revenue, 0)) as total_revenue,
			SUM(IFNULL(t.distance_loaded, 0) + IFNULL(t.extra_distance_loaded, 0)) as loaded_km,
			SUM(IFNULL(t.distance_empty, 0) + IFNULL(t.extra_distance_empty, 0)) as empty_km
		FROM `tabTrip` t
		WHERE {where_clause}
		GROUP BY t.truck
		ORDER BY t.truck
	""".format(where_clause=where_clause), params, as_dict=True)

	# Fuel allocated per truck
	fuel_map = {}
	fuel_rows = frappe.db.sql("""
		SELECT t.truck, SUM(IFNULL(fa.qty, 0)) as fuel_litres, SUM(IFNULL(fa.amount, 0)) as fuel_cost
		FROM `tabTrip Fuel Allocation` fa
		INNER JOIN `tabTrip` t ON fa.parent = t.name
		WHERE {where_clause}
		GROUP BY t.truck
	""".format(where_clause=where_clause), params, as_dict=True)
	for r in fuel_rows:
		fuel_map[r.truck] = {"litres": flt(r.fuel_litres), "cost": flt(r.fuel_cost)}

	# Standard consumption rates from Truck master
	truck_standards = {}
	truck_names = [t.truck for t in trucks if t.truck]
	if truck_names:
		for tn in truck_names:
			std = frappe.db.get_value("Truck", tn,
				["loaded_fuel_consumption", "empty_fuel_consumption"], as_dict=True)
			if std:
				truck_standards[tn] = std

	data = []
	for row in trucks:
		total_km = flt(row.loaded_km) + flt(row.empty_km)
		fuel_info = fuel_map.get(row.truck, {"litres": 0, "cost": 0})
		actual_litres = flt(fuel_info["litres"])
		fuel_cost = flt(fuel_info["cost"])
		revenue = flt(row.total_revenue)

		# Actual consumption
		actual_kpl = (total_km / actual_litres) if actual_litres else 0

		# Expected consumption based on truck standards
		std = truck_standards.get(row.truck, {})
		std_loaded = flt(std.get("loaded_fuel_consumption", 0))
		std_empty = flt(std.get("empty_fuel_consumption", 0))

		expected_litres = 0
		if std_loaded:
			expected_litres += flt(row.loaded_km) / std_loaded
		if std_empty:
			expected_litres += flt(row.empty_km) / std_empty

		variance = actual_litres - expected_litres
		variance_pct = (variance / expected_litres * 100) if expected_litres else 0
		fuel_pct_of_revenue = (fuel_cost / revenue * 100) if revenue else 0

		data.append({
			"truck": row.truck,
			"trip_count": row.trip_count,
			"total_km": flt(total_km, 0),
			"actual_litres": flt(actual_litres, 2),
			"expected_litres": flt(expected_litres, 2),
			"variance_litres": flt(variance, 2),
			"variance_percent": flt(variance_pct, 1),
			"actual_kpl": flt(actual_kpl, 2),
			"fuel_cost": flt(fuel_cost, 2),
			"fuel_pct_of_revenue": flt(fuel_pct_of_revenue, 1),
			"revenue": flt(revenue, 2),
		})

	return data


def get_columns():
	return [
		{"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 110},
		{"label": "Trips", "fieldname": "trip_count", "fieldtype": "Int", "width": 60},
		{"label": "Total Km", "fieldname": "total_km", "fieldtype": "Float", "width": 90},
		{"label": "Actual (L)", "fieldname": "actual_litres", "fieldtype": "Float", "width": 90},
		{"label": "Expected (L)", "fieldname": "expected_litres", "fieldtype": "Float", "width": 100},
		{"label": "Variance (L)", "fieldname": "variance_litres", "fieldtype": "Float", "width": 100},
		{"label": "Variance %", "fieldname": "variance_percent", "fieldtype": "Percent", "width": 90},
		{"label": "Km/L", "fieldname": "actual_kpl", "fieldtype": "Float", "width": 70},
		{"label": "Fuel Cost", "fieldname": "fuel_cost", "fieldtype": "Currency", "width": 110},
		{"label": "Fuel % Rev", "fieldname": "fuel_pct_of_revenue", "fieldtype": "Percent", "width": 100},
		{"label": "Revenue", "fieldname": "revenue", "fieldtype": "Currency", "width": 120},
	]
