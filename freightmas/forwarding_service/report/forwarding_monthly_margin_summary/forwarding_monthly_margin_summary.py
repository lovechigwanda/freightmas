# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import calendar

import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)


def get_data(filters):
	"""Monthly margin based on recognized jobs and submitted forwarding invoices."""
	conditions = [
		"fj.docstatus = 1",
		"fj.revenue_recognised = 1",
		"fj.revenue_recognised_on IS NOT NULL",
	]
	params = {}

	if filters.get("from_date"):
		conditions.append("fj.revenue_recognised_on >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("fj.revenue_recognised_on <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("company"):
		conditions.append("fj.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("customer"):
		conditions.append("fj.customer = %(customer)s")
		params["customer"] = filters["customer"]

	if filters.get("shipment_mode"):
		conditions.append("fj.shipment_mode = %(shipment_mode)s")
		params["shipment_mode"] = filters["shipment_mode"]

	if filters.get("direction"):
		conditions.append("fj.direction = %(direction)s")
		params["direction"] = filters["direction"]

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql(
		"""
		SELECT
			YEAR(fj.revenue_recognised_on) AS year_num,
			MONTH(fj.revenue_recognised_on) AS month_num,
			COUNT(DISTINCT fj.name) AS shipment_count,
			SUM(IFNULL(cpd_totals.container_count, 0)) AS container_count,
			SUM(IFNULL(si_totals.actual_revenue, 0)) AS total_revenue,
			SUM(IFNULL(pi_totals.actual_cost, 0)) AS total_cost
		FROM `tabForwarding Job` fj
		LEFT JOIN (
			SELECT
				si.forwarding_job_reference AS job_ref,
				SUM(si.base_grand_total) AS actual_revenue
			FROM `tabSales Invoice` si
			WHERE si.docstatus = 1
				AND si.is_forwarding_invoice = 1
				AND si.forwarding_job_reference IS NOT NULL
			GROUP BY si.forwarding_job_reference
		) si_totals ON si_totals.job_ref = fj.name
		LEFT JOIN (
			SELECT
				pi.forwarding_job_reference AS job_ref,
				SUM(pi.base_grand_total) AS actual_cost
			FROM `tabPurchase Invoice` pi
			WHERE pi.docstatus = 1
				AND pi.is_forwarding_invoice = 1
				AND pi.forwarding_job_reference IS NOT NULL
			GROUP BY pi.forwarding_job_reference
		) pi_totals ON pi_totals.job_ref = fj.name
		LEFT JOIN (
			SELECT
				cpd.parent AS job_ref,
				COUNT(cpd.name) AS container_count
			FROM `tabCargo Parcel Details` cpd
			WHERE cpd.cargo_type = 'Containerised'
			GROUP BY cpd.parent
		) cpd_totals ON cpd_totals.job_ref = fj.name
		WHERE {where_clause}
		GROUP BY year_num, month_num
		ORDER BY year_num, month_num
		""".format(where_clause=where_clause),
		params,
		as_dict=True,
	)

	data = []
	for row in rows:
		month_name = calendar.month_abbr[row.month_num] if row.month_num else ""
		revenue = flt(row.total_revenue, 2)
		cost = flt(row.total_cost, 2)
		margin = flt(revenue - cost, 2)
		margin_percent = flt((margin / revenue) * 100, 1) if revenue else 0

		data.append(
			{
				"period": f"{month_name} {row.year_num}",
				"shipment_count": row.shipment_count,
				"container_count": int(row.container_count or 0),
				"total_revenue": revenue,
				"total_cost": cost,
				"total_margin": margin,
				"margin_percent": margin_percent,
			}
		)

	return data


def get_columns():
	return [
		{"label": "Period", "fieldname": "period", "fieldtype": "Data", "width": 110},
		{"label": "Shipments", "fieldname": "shipment_count", "fieldtype": "Int", "width": 100},
		{"label": "Containers", "fieldname": "container_count", "fieldtype": "Int", "width": 100},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 140},
		{"label": "Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 140},
		{"label": "Margin", "fieldname": "total_margin", "fieldtype": "Currency", "width": 140},
		{"label": "Margin %", "fieldname": "margin_percent", "fieldtype": "Percent", "width": 100},
	]
