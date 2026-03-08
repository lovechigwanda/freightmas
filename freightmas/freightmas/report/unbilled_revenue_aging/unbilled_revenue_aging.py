# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, date_diff, getdate, today


CHARGE_TABLES = [
	{
		"service": "Forwarding",
		"child_table": "Forwarding Revenue Charges",
		"parent_table": "Forwarding Job",
		"child_field": "forwarding_revenue_charges",
		"customer_field": "customer",
		"amount_field": "revenue_amount",
		"parent_date_field": "date_created",
	},
	{
		"service": "Clearing",
		"child_table": "Clearing Revenue Charges",
		"parent_table": "Clearing Job",
		"child_field": "clearing_revenue_charges",
		"customer_field": "customer",
		"amount_field": "revenue_amount",
		"parent_date_field": "date_created",
	},
	{
		"service": "Trucking",
		"child_table": "Trip Revenue Charges",
		"parent_table": "Trip",
		"child_field": "trip_revenue_charges",
		"customer_field": "receivable_party",
		"amount_field": "total_amount",
		"parent_date_field": "date_created",
	},
	{
		"service": "Road Freight",
		"child_table": "Road Freight Charges",
		"parent_table": "Road Freight Job",
		"child_field": "road_freight_charges",
		"customer_field": "customer",
		"amount_field": "revenue_amount",
		"parent_date_field": "date_created",
	},
]


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_data(filters):
	as_of = getdate(filters.get("as_of_date") or today())
	company = filters.get("company")
	service_filter = filters.get("service")

	results = {}  # keyed by (customer, service)

	for cfg in CHARGE_TABLES:
		if service_filter and cfg["service"] != service_filter:
			continue

		try:
			_collect_unbilled(cfg, as_of, company, results)
		except Exception:
			# Table might not exist in some installations
			continue

	data = []
	for key, row in sorted(results.items(), key=lambda x: -(x[1]["total"])):
		data.append(row)

	return data


def _collect_unbilled(cfg, as_of, company, results):
	conditions = ["c.is_invoiced = 0", "p.docstatus < 2"]
	params = {}

	if company:
		conditions.append("p.company = %(company)s")
		params["company"] = company

	where = " AND ".join(conditions)

	rows = frappe.db.sql("""
		SELECT
			c.{customer} as customer,
			c.{amount} as amount,
			p.{date_field} as job_date,
			p.name as job_name
		FROM `tab{child}` c
		INNER JOIN `tab{parent}` p ON p.name = c.parent
		WHERE {where}
	""".format(
		customer=cfg["customer_field"],
		amount=cfg["amount_field"],
		date_field=cfg["parent_date_field"],
		child=cfg["child_table"],
		parent=cfg["parent_table"],
		where=where,
	), params, as_dict=True)

	for r in rows:
		if not r.amount or flt(r.amount) <= 0:
			continue

		days = date_diff(as_of, r.job_date) if r.job_date else 0
		key = (r.customer or "Unknown", cfg["service"])

		if key not in results:
			results[key] = {
				"customer": r.customer or "Unknown",
				"service": cfg["service"],
				"current": 0,
				"days_31_60": 0,
				"days_61_90": 0,
				"over_90": 0,
				"total": 0,
			}

		amt = flt(r.amount, 2)
		entry = results[key]

		if days <= 30:
			entry["current"] += amt
		elif days <= 60:
			entry["days_31_60"] += amt
		elif days <= 90:
			entry["days_61_90"] += amt
		else:
			entry["over_90"] += amt

		entry["total"] += amt


def get_columns():
	return [
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": "Service", "fieldname": "service", "fieldtype": "Data", "width": 120},
		{"label": "0 - 30 Days", "fieldname": "current", "fieldtype": "Currency", "width": 130},
		{"label": "31 - 60 Days", "fieldname": "days_31_60", "fieldtype": "Currency", "width": 130},
		{"label": "61 - 90 Days", "fieldname": "days_61_90", "fieldtype": "Currency", "width": 130},
		{"label": "Over 90 Days", "fieldname": "over_90", "fieldtype": "Currency", "width": 130},
		{"label": "Total Unbilled", "fieldname": "total", "fieldtype": "Currency", "width": 140},
	]
