# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
import calendar


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

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql("""
		SELECT
			YEAR(fj.date_created) as year_num,
			MONTH(fj.date_created) as month_num,
			fj.shipment_mode,
			fj.direction,
			COUNT(fj.name) as jobs_opened,
			COUNT(CASE WHEN fj.status = 'Completed' THEN 1 END) as jobs_completed,
			SUM(IFNULL(fj.total_working_revenue_base, 0)) as total_revenue,
			SUM(IFNULL(fj.total_working_base, 0)) as total_cost,
			SUM(IFNULL(fj.total_working_profit_base, 0)) as total_profit
		FROM `tabForwarding Job` fj
		WHERE {where_clause}
		GROUP BY year_num, month_num, fj.shipment_mode, fj.direction
		ORDER BY year_num, month_num, fj.shipment_mode, fj.direction
	""".format(where_clause=where_clause), params, as_dict=True)

	data = []
	for row in rows:
		month_name = calendar.month_abbr[row.month_num] if row.month_num else ""
		revenue = flt(row.total_revenue)
		profit = flt(row.total_profit)
		margin_pct = (profit / revenue * 100) if revenue else 0
		job_type = " ".join(filter(None, [row.shipment_mode, row.direction]))

		data.append({
			"period": f"{month_name} {row.year_num}",
			"job_type": job_type,
			"jobs_opened": row.jobs_opened,
			"jobs_completed": row.jobs_completed,
			"total_revenue": flt(revenue, 2),
			"total_cost": flt(row.total_cost, 2),
			"total_profit": flt(profit, 2),
			"margin_percent": flt(margin_pct, 1),
		})

	return data


def get_columns():
	return [
		{"label": "Period", "fieldname": "period", "fieldtype": "Data", "width": 110},
		{"label": "Job Type", "fieldname": "job_type", "fieldtype": "Data", "width": 140},
		{"label": "Jobs Opened", "fieldname": "jobs_opened", "fieldtype": "Int", "width": 100},
		{"label": "Jobs Completed", "fieldname": "jobs_completed", "fieldtype": "Int", "width": 110},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 130},
		{"label": "Profit", "fieldname": "total_profit", "fieldtype": "Currency", "width": 130},
		{"label": "Margin %", "fieldname": "margin_percent", "fieldtype": "Percent", "width": 100},
	]
