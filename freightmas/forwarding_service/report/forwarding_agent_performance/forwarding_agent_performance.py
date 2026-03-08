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
	conditions = ["fj.docstatus < 2", "fj.origin_agent IS NOT NULL", "fj.origin_agent != ''"]
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

	if filters.get("origin_agent"):
		conditions.append("fj.origin_agent = %(origin_agent)s")
		params["origin_agent"] = filters["origin_agent"]

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql("""
		SELECT
			fj.origin_agent,
			COUNT(fj.name) as job_count,
			SUM(IFNULL(fj.total_working_revenue_base, 0)) as total_revenue,
			SUM(IFNULL(fj.total_working_base, 0)) as total_cost,
			SUM(IFNULL(fj.total_working_profit_base, 0)) as total_profit,
			COUNT(CASE WHEN fj.status = 'Completed' THEN 1 END) as completed_jobs
		FROM `tabForwarding Job` fj
		WHERE {where_clause}
		GROUP BY fj.origin_agent
		ORDER BY total_revenue DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	data = []
	for row in rows:
		revenue = flt(row.total_revenue)
		profit = flt(row.total_profit)
		margin_pct = (profit / revenue * 100) if revenue else 0
		avg_revenue = (revenue / row.job_count) if row.job_count else 0

		data.append({
			"origin_agent": row.origin_agent,
			"job_count": row.job_count,
			"completed_jobs": row.completed_jobs,
			"total_revenue": flt(revenue, 2),
			"total_cost": flt(row.total_cost, 2),
			"total_profit": flt(profit, 2),
			"margin_percent": flt(margin_pct, 1),
			"avg_revenue_per_job": flt(avg_revenue, 2),
		})

	return data


def get_columns():
	return [
		{"label": "Origin Agent", "fieldname": "origin_agent", "fieldtype": "Link", "options": "Supplier", "width": 200},
		{"label": "Jobs", "fieldname": "job_count", "fieldtype": "Int", "width": 70},
		{"label": "Completed", "fieldname": "completed_jobs", "fieldtype": "Int", "width": 90},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 130},
		{"label": "Profit", "fieldname": "total_profit", "fieldtype": "Currency", "width": 130},
		{"label": "Margin %", "fieldname": "margin_percent", "fieldtype": "Percent", "width": 100},
		{"label": "Avg Rev/Job", "fieldname": "avg_revenue_per_job", "fieldtype": "Currency", "width": 130},
	]
