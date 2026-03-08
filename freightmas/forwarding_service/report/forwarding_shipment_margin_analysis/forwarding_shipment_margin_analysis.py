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
	"""Get shipment margin analysis based on revenue recognition date
	and actual invoiced amounts (Sales Invoices, Credit Notes, Purchase Invoices, Debit Notes).
	"""
	conditions = ["fj.docstatus < 2", "fj.revenue_recognised = 1"]
	params = {}

	if filters.get("from_date"):
		conditions.append("fj.revenue_recognised_on >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("fj.revenue_recognised_on <= %(to_date)s")
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

	# Get recognised jobs with actual revenue/cost from submitted invoices
	jobs = frappe.db.sql("""
		SELECT
			fj.shipment_mode,
			fj.direction,
			fj.customer,
			COUNT(DISTINCT fj.name) AS job_count,
			IFNULL(SUM(si_totals.actual_revenue), 0) AS total_revenue,
			IFNULL(SUM(pi_totals.actual_cost), 0) AS total_cost
		FROM `tabForwarding Job` fj
		LEFT JOIN (
			SELECT
				si.custom_forwarding_job_reference AS job_ref,
				SUM(si.base_grand_total) AS actual_revenue
			FROM `tabSales Invoice` si
			WHERE si.docstatus = 1
				AND si.custom_is_forwarding_invoice = 1
				AND si.custom_forwarding_job_reference IS NOT NULL
			GROUP BY si.custom_forwarding_job_reference
		) si_totals ON si_totals.job_ref = fj.name
		LEFT JOIN (
			SELECT
				pi.custom_forwarding_job_reference AS job_ref,
				SUM(pi.base_grand_total) AS actual_cost
			FROM `tabPurchase Invoice` pi
			WHERE pi.docstatus = 1
				AND pi.custom_is_forwarding_invoice = 1
				AND pi.custom_forwarding_job_reference IS NOT NULL
			GROUP BY pi.custom_forwarding_job_reference
		) pi_totals ON pi_totals.job_ref = fj.name
		WHERE {where_clause}
		GROUP BY fj.shipment_mode, fj.direction, fj.customer
		ORDER BY fj.shipment_mode, fj.direction,
			(IFNULL(SUM(si_totals.actual_revenue), 0) - IFNULL(SUM(pi_totals.actual_cost), 0)) DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	data = []
	for row in jobs:
		revenue = flt(row.total_revenue, 2)
		cost = flt(row.total_cost, 2)
		profit = flt(revenue - cost, 2)
		margin_pct = (profit / revenue * 100) if revenue else 0
		data.append({
			"shipment_mode": row.shipment_mode,
			"direction": row.direction,
			"customer": row.customer,
			"job_count": row.job_count,
			"total_revenue": revenue,
			"total_cost": cost,
			"total_profit": profit,
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
