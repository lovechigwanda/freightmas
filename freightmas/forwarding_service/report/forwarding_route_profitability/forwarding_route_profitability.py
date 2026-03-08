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
	conditions = ["fj.docstatus < 2"]
	params = {}

	if filters.get("from_date"):
		conditions.append("fj.date_created >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("fj.date_created <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("company"):
		conditions.append("fj.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("direction"):
		conditions.append("fj.direction = %(direction)s")
		params["direction"] = filters["direction"]

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql("""
		SELECT
			CONCAT(IFNULL(fj.port_of_loading, ''), ' → ', IFNULL(fj.port_of_discharge, '')) as trade_lane,
			fj.port_of_loading,
			fj.port_of_discharge,
			fj.direction,
			COUNT(fj.name) as job_count,
			SUM(IFNULL(fj.total_working_revenue_base, 0)) as total_revenue,
			SUM(IFNULL(fj.total_working_base, 0)) as total_cost,
			SUM(IFNULL(fj.total_working_profit_base, 0)) as total_profit
		FROM `tabForwarding Job` fj
		WHERE {where_clause}
		GROUP BY fj.port_of_loading, fj.port_of_discharge, fj.direction
		ORDER BY total_profit DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	# Get container (TEU) counts per route
	teu_map = {}
	parcels = frappe.db.sql("""
		SELECT
			CONCAT(IFNULL(fj.port_of_loading, ''), ' → ', IFNULL(fj.port_of_discharge, '')) as trade_lane,
			COUNT(cpd.name) as cnt
		FROM `tabCargo Parcel Details` cpd
		INNER JOIN `tabForwarding Job` fj ON cpd.parent = fj.name
		WHERE {where_clause}
		GROUP BY trade_lane
	""".format(where_clause=where_clause), params, as_dict=True)
	for p in parcels:
		teu_map[p.trade_lane] = p.cnt

	data = []
	for row in rows:
		revenue = flt(row.total_revenue)
		profit = flt(row.total_profit)
		margin_pct = (profit / revenue * 100) if revenue else 0
		containers = teu_map.get(row.trade_lane, 0)
		avg_margin = (profit / row.job_count) if row.job_count else 0

		data.append({
			"trade_lane": row.trade_lane,
			"direction": row.direction,
			"job_count": row.job_count,
			"containers": containers,
			"total_revenue": flt(revenue, 2),
			"total_cost": flt(row.total_cost, 2),
			"total_profit": flt(profit, 2),
			"margin_percent": flt(margin_pct, 1),
			"avg_margin_per_job": flt(avg_margin, 2),
		})

	return data


def get_columns():
	return [
		{"label": "Trade Lane", "fieldname": "trade_lane", "fieldtype": "Data", "width": 220},
		{"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 100},
		{"label": "Jobs", "fieldname": "job_count", "fieldtype": "Int", "width": 70},
		{"label": "Containers", "fieldname": "containers", "fieldtype": "Int", "width": 100},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 130},
		{"label": "Profit", "fieldname": "total_profit", "fieldtype": "Currency", "width": 130},
		{"label": "Margin %", "fieldname": "margin_percent", "fieldtype": "Percent", "width": 100},
		{"label": "Avg Margin/Job", "fieldname": "avg_margin_per_job", "fieldtype": "Currency", "width": 130},
	]
