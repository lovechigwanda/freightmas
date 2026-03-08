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
	date_conditions = ""
	params = {}

	if filters.get("from_date"):
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		params["to_date"] = filters["to_date"]
	if filters.get("company"):
		params["company"] = filters["company"]

	data = []

	# Forwarding Jobs
	fj = _get_service_stats("Forwarding Job", "creation", "total_working_revenue_base",
		"total_working_base", "total_working_profit_base", filters, params)
	if fj:
		data.append({**fj, "service": "Forwarding"})

	# Clearing Jobs
	cj = _get_service_stats("Clearing Job", "creation", "total_revenue_base",
		"total_cost_base", "total_profit_base", filters, params)
	if cj:
		data.append({**cj, "service": "Clearing"})

	# Trucking (Trips)
	trip = _get_trip_stats(filters, params)
	if trip:
		data.append({**trip, "service": "Trucking"})

	# Road Freight Jobs
	rf = _get_service_stats("Road Freight Job", "creation", "total_revenue_base",
		"total_cost_base", "total_profit_base", filters, params)
	if rf:
		data.append({**rf, "service": "Road Freight"})

	# Totals row
	if data:
		totals = {
			"service": "TOTAL",
			"job_count": sum(r.get("job_count", 0) for r in data),
			"total_revenue": sum(r.get("total_revenue", 0) for r in data),
			"total_cost": sum(r.get("total_cost", 0) for r in data),
			"total_profit": sum(r.get("total_profit", 0) for r in data),
		}
		totals["margin_pct"] = flt(totals["total_profit"] / totals["total_revenue"] * 100, 1) if totals["total_revenue"] else 0
		data.append(totals)

	return data


def _get_service_stats(doctype, date_field, revenue_field, cost_field, profit_field, filters, params):
	conditions = ["docstatus < 2"]
	local_params = dict(params)

	if filters.get("from_date"):
		conditions.append(f"{date_field} >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append(f"{date_field} <= %(to_date)s")
	if filters.get("company"):
		conditions.append("company = %(company)s")

	where = " AND ".join(conditions)

	try:
		row = frappe.db.sql("""
			SELECT
				COUNT(name) as job_count,
				SUM(IFNULL({revenue}, 0)) as total_revenue,
				SUM(IFNULL({cost}, 0)) as total_cost,
				SUM(IFNULL({profit}, 0)) as total_profit
			FROM `tab{doctype}`
			WHERE {where}
		""".format(revenue=revenue_field, cost=cost_field, profit=profit_field,
			doctype=doctype, where=where), local_params, as_dict=True)
	except Exception:
		return None

	if row and row[0]:
		r = row[0]
		margin = flt(r.total_profit / r.total_revenue * 100, 1) if r.total_revenue else 0
		return {
			"job_count": r.job_count or 0,
			"total_revenue": flt(r.total_revenue, 2),
			"total_cost": flt(r.total_cost, 2),
			"total_profit": flt(r.total_profit, 2),
			"margin_pct": margin,
		}
	return None


def _get_trip_stats(filters, params):
	conditions = ["docstatus < 2"]
	local_params = dict(params)

	if filters.get("from_date"):
		conditions.append("date_created >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("date_created <= %(to_date)s")
	if filters.get("company"):
		conditions.append("company = %(company)s")

	where = " AND ".join(conditions)

	try:
		row = frappe.db.sql("""
			SELECT
				COUNT(name) as job_count,
				SUM(IFNULL(total_estimated_revenue, 0)) as total_revenue,
				SUM(IFNULL(total_estimated_cost, 0)) as total_cost,
				SUM(IFNULL(total_estimated_revenue, 0) - IFNULL(total_estimated_cost, 0)) as total_profit
			FROM `tabTrip`
			WHERE {where}
		""".format(where=where), local_params, as_dict=True)
	except Exception:
		return None

	if row and row[0]:
		r = row[0]
		margin = flt(r.total_profit / r.total_revenue * 100, 1) if r.total_revenue else 0
		return {
			"job_count": r.job_count or 0,
			"total_revenue": flt(r.total_revenue, 2),
			"total_cost": flt(r.total_cost, 2),
			"total_profit": flt(r.total_profit, 2),
			"margin_pct": margin,
		}
	return None


def get_columns():
	return [
		{"label": "Service", "fieldname": "service", "fieldtype": "Data", "width": 160},
		{"label": "Jobs/Trips", "fieldname": "job_count", "fieldtype": "Int", "width": 100},
		{"label": "Total Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 150},
		{"label": "Total Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 150},
		{"label": "Total Profit", "fieldname": "total_profit", "fieldtype": "Currency", "width": 150},
		{"label": "Margin %", "fieldname": "margin_pct", "fieldtype": "Percent", "width": 100},
	]
