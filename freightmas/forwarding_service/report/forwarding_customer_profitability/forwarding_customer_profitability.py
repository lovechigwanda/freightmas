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

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql("""
		SELECT
			fj.customer,
			COUNT(fj.name) as job_count,
			SUM(IFNULL(fj.total_working_revenue_base, 0)) as total_revenue,
			SUM(IFNULL(fj.total_working_base, 0)) as total_cost,
			SUM(IFNULL(fj.total_working_profit_base, 0)) as total_profit
		FROM `tabForwarding Job` fj
		WHERE {where_clause}
		GROUP BY fj.customer
		ORDER BY total_profit DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	# Get container counts per customer
	container_counts = {}
	if rows:
		customer_list = [r.customer for r in rows if r.customer]
		if customer_list:
			parcels = frappe.db.sql("""
				SELECT fj.customer, COUNT(cpd.name) as cnt
				FROM `tabCargo Parcel Details` cpd
				INNER JOIN `tabForwarding Job` fj ON cpd.parent = fj.name
				WHERE {where_clause}
				GROUP BY fj.customer
			""".format(where_clause=where_clause), params, as_dict=True)
			for p in parcels:
				container_counts[p.customer] = p.cnt

	data = []
	rank = 0
	for row in rows:
		rank += 1
		revenue = flt(row.total_revenue)
		cost = flt(row.total_cost)
		profit = flt(row.total_profit)
		margin_pct = (profit / revenue * 100) if revenue else 0
		containers = container_counts.get(row.customer, 0)
		rev_per_container = (revenue / containers) if containers else 0

		data.append({
			"rank": rank,
			"customer": row.customer,
			"job_count": row.job_count,
			"containers": containers,
			"total_revenue": flt(revenue, 2),
			"total_cost": flt(cost, 2),
			"total_profit": flt(profit, 2),
			"margin_percent": flt(margin_pct, 1),
			"revenue_per_container": flt(rev_per_container, 2),
		})

	return data


def get_columns():
	return [
		{"label": "#", "fieldname": "rank", "fieldtype": "Int", "width": 50},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": "Jobs", "fieldname": "job_count", "fieldtype": "Int", "width": 70},
		{"label": "Containers", "fieldname": "containers", "fieldtype": "Int", "width": 100},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 130},
		{"label": "Profit", "fieldname": "total_profit", "fieldtype": "Currency", "width": 130},
		{"label": "Margin %", "fieldname": "margin_percent", "fieldtype": "Percent", "width": 100},
		{"label": "Rev/Container", "fieldname": "revenue_per_container", "fieldtype": "Currency", "width": 130},
	]
