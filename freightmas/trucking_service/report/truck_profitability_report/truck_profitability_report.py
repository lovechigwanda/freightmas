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

	# Aggregate trips per truck
	trucks = frappe.db.sql("""
		SELECT
			t.truck,
			COUNT(t.name) as trip_count,
			SUM(IFNULL(t.total_estimated_revenue, 0)) as total_revenue,
			SUM(IFNULL(t.distance_loaded, 0) + IFNULL(t.extra_distance_loaded, 0)) as total_loaded_km,
			SUM(IFNULL(t.distance_empty, 0) + IFNULL(t.extra_distance_empty, 0)) as total_empty_km
		FROM `tabTrip` t
		WHERE {where_clause}
		GROUP BY t.truck
		ORDER BY total_revenue DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	# Get fuel costs per truck
	fuel_costs = {}
	fuel_rows = frappe.db.sql("""
		SELECT t.truck, SUM(IFNULL(fa.amount, 0)) as fuel_cost
		FROM `tabTrip Fuel Allocation` fa
		INNER JOIN `tabTrip` t ON fa.parent = t.name
		WHERE {where_clause}
		GROUP BY t.truck
	""".format(where_clause=where_clause), params, as_dict=True)
	for r in fuel_rows:
		fuel_costs[r.truck] = flt(r.fuel_cost)

	# Get other costs per truck
	other_costs = {}
	cost_rows = frappe.db.sql("""
		SELECT t.truck, SUM(IFNULL(oc.total_amount, 0)) as other_cost
		FROM `tabTrip Other Costs` oc
		INNER JOIN `tabTrip` t ON oc.parent = t.name
		WHERE {where_clause}
		GROUP BY t.truck
	""".format(where_clause=where_clause), params, as_dict=True)
	for r in cost_rows:
		other_costs[r.truck] = flt(r.other_cost)

	data = []
	for row in trucks:
		revenue = flt(row.total_revenue)
		fuel = flt(fuel_costs.get(row.truck, 0))
		other = flt(other_costs.get(row.truck, 0))
		total_cost = fuel + other
		profit = revenue - total_cost
		total_km = flt(row.total_loaded_km) + flt(row.total_empty_km)
		rev_per_km = (revenue / total_km) if total_km else 0
		cost_per_km = (total_cost / total_km) if total_km else 0
		margin_pct = (profit / revenue * 100) if revenue else 0

		data.append({
			"truck": row.truck,
			"trip_count": row.trip_count,
			"total_revenue": flt(revenue, 2),
			"fuel_cost": flt(fuel, 2),
			"other_cost": flt(other, 2),
			"total_cost": flt(total_cost, 2),
			"profit": flt(profit, 2),
			"margin_percent": flt(margin_pct, 1),
			"total_km": flt(total_km, 0),
			"revenue_per_km": flt(rev_per_km, 2),
			"cost_per_km": flt(cost_per_km, 2),
		})

	return data


def get_columns():
	return [
		{"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 110},
		{"label": "Trips", "fieldname": "trip_count", "fieldtype": "Int", "width": 70},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 120},
		{"label": "Fuel Cost", "fieldname": "fuel_cost", "fieldtype": "Currency", "width": 110},
		{"label": "Other Costs", "fieldname": "other_cost", "fieldtype": "Currency", "width": 110},
		{"label": "Total Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 110},
		{"label": "Profit", "fieldname": "profit", "fieldtype": "Currency", "width": 120},
		{"label": "Margin %", "fieldname": "margin_percent", "fieldtype": "Percent", "width": 90},
		{"label": "Total Km", "fieldname": "total_km", "fieldtype": "Float", "width": 90},
		{"label": "Rev/Km", "fieldname": "revenue_per_km", "fieldtype": "Currency", "width": 100},
		{"label": "Cost/Km", "fieldname": "cost_per_km", "fieldtype": "Currency", "width": 100},
	]
