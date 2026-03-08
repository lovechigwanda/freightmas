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

	if filters.get("customer"):
		conditions.append("fj.customer = %(customer)s")
		params["customer"] = filters["customer"]

	if filters.get("shipment_mode"):
		conditions.append("fj.shipment_mode = %(shipment_mode)s")
		params["shipment_mode"] = filters["shipment_mode"]

	if filters.get("direction"):
		conditions.append("fj.direction = %(direction)s")
		params["direction"] = filters["direction"]

	if filters.get("company"):
		conditions.append("fj.company = %(company)s")
		params["company"] = filters["company"]

	where_clause = " AND ".join(conditions)

	jobs = frappe.db.sql("""
		SELECT
			fj.shipment_mode,
			fj.direction,
			fj.customer,
			COUNT(fj.name) as job_count,
			SUM(IFNULL(fj.total_working_revenue_base, 0)) as total_revenue,
			SUM(IFNULL(fj.total_working_base, 0)) as total_cost,
			SUM(IFNULL(fj.total_working_profit_base, 0)) as total_profit
		FROM `tabForwarding Job` fj
		WHERE {where_clause}
		GROUP BY fj.shipment_mode, fj.direction, fj.customer
		ORDER BY fj.shipment_mode, fj.direction, total_profit DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	data = []
	for row in jobs:
		margin_pct = (flt(row.total_profit) / flt(row.total_revenue) * 100) if flt(row.total_revenue) else 0
		data.append({
			"shipment_mode": row.shipment_mode,
			"direction": row.direction,
			"customer": row.customer,
			"job_count": row.job_count,
			"total_revenue": flt(row.total_revenue, 2),
			"total_cost": flt(row.total_cost, 2),
			"total_profit": flt(row.total_profit, 2),
			"margin_percent": flt(margin_pct, 1),
		})

	return data


def get_columns():
	return [
		{"label": "Shipment Mode", "fieldname": "shipment_mode", "fieldtype": "Data", "width": 120},
		{"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 100},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": "Jobs", "fieldname": "job_count", "fieldtype": "Int", "width": 70},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 130},
		{"label": "Profit", "fieldname": "total_profit", "fieldtype": "Currency", "width": 130},
		{"label": "Margin %", "fieldname": "margin_percent", "fieldtype": "Percent", "width": 100},
	]
