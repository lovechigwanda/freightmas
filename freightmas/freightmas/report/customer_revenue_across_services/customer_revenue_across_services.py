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
	params = {}
	date_conditions_clearing = []
	date_conditions_forwarding = []
	date_conditions_trip = []
	date_conditions_rf = []

	if filters.get("from_date"):
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		params["to_date"] = filters["to_date"]
	if filters.get("company"):
		params["company"] = filters["company"]

	customers = {}  # customer → {forwarding, clearing, trucking, road_freight, total}

	# Forwarding
	_collect_forwarding(filters, params, customers)

	# Clearing
	_collect_clearing(filters, params, customers)

	# Trucking
	_collect_trucking(filters, params, customers)

	# Road Freight
	_collect_road_freight(filters, params, customers)

	# Build rows sorted by total descending
	data = []
	for customer, vals in sorted(customers.items(), key=lambda x: -x[1].get("total_revenue", 0)):
		total = flt(vals.get("forwarding", 0) + vals.get("clearing", 0) +
			vals.get("trucking", 0) + vals.get("road_freight", 0), 2)
		data.append({
			"customer": customer,
			"forwarding_revenue": flt(vals.get("forwarding", 0), 2),
			"clearing_revenue": flt(vals.get("clearing", 0), 2),
			"trucking_revenue": flt(vals.get("trucking", 0), 2),
			"road_freight_revenue": flt(vals.get("road_freight", 0), 2),
			"total_revenue": total,
			"service_count": sum(1 for k in ["forwarding", "clearing", "trucking", "road_freight"] if vals.get(k, 0) > 0),
		})

	return data


def _build_conditions(filters, params, date_field, alias="p"):
	conditions = [f"{alias}.docstatus < 2"]
	if filters.get("from_date"):
		conditions.append(f"{alias}.{date_field} >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append(f"{alias}.{date_field} <= %(to_date)s")
	if filters.get("company"):
		conditions.append(f"{alias}.company = %(company)s")
	return " AND ".join(conditions)


def _collect_forwarding(filters, params, customers):
	where = _build_conditions(filters, params, "date_created")
	try:
		rows = frappe.db.sql("""
			SELECT customer, SUM(IFNULL(total_working_revenue_base, 0)) as revenue
			FROM `tabForwarding Job` p
			WHERE {where}
			GROUP BY customer
		""".format(where=where), params, as_dict=True)
		for r in rows:
			if r.customer:
				customers.setdefault(r.customer, {})["forwarding"] = flt(r.revenue, 2)
				customers[r.customer]["total_revenue"] = customers[r.customer].get("total_revenue", 0) + flt(r.revenue, 2)
	except Exception:
		pass


def _collect_clearing(filters, params, customers):
	where = _build_conditions(filters, params, "date_created")
	try:
		rows = frappe.db.sql("""
			SELECT customer, SUM(IFNULL(total_revenue_base, 0)) as revenue
			FROM `tabClearing Job` p
			WHERE {where}
			GROUP BY customer
		""".format(where=where), params, as_dict=True)
		for r in rows:
			if r.customer:
				customers.setdefault(r.customer, {})["clearing"] = flt(r.revenue, 2)
				customers[r.customer]["total_revenue"] = customers[r.customer].get("total_revenue", 0) + flt(r.revenue, 2)
	except Exception:
		pass


def _collect_trucking(filters, params, customers):
	where = _build_conditions(filters, params, "date_created")
	try:
		rows = frappe.db.sql("""
			SELECT customer, SUM(IFNULL(total_estimated_revenue, 0)) as revenue
			FROM `tabTrip` p
			WHERE {where}
			GROUP BY customer
		""".format(where=where), params, as_dict=True)
		for r in rows:
			if r.customer:
				customers.setdefault(r.customer, {})["trucking"] = flt(r.revenue, 2)
				customers[r.customer]["total_revenue"] = customers[r.customer].get("total_revenue", 0) + flt(r.revenue, 2)
	except Exception:
		pass


def _collect_road_freight(filters, params, customers):
	where = _build_conditions(filters, params, "date_created")
	try:
		rows = frappe.db.sql("""
			SELECT customer, SUM(IFNULL(total_revenue_base, 0)) as revenue
			FROM `tabRoad Freight Job` p
			WHERE {where}
			GROUP BY customer
		""".format(where=where), params, as_dict=True)
		for r in rows:
			if r.customer:
				customers.setdefault(r.customer, {})["road_freight"] = flt(r.revenue, 2)
				customers[r.customer]["total_revenue"] = customers[r.customer].get("total_revenue", 0) + flt(r.revenue, 2)
	except Exception:
		pass


def get_columns():
	return [
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 220},
		{"label": "Forwarding", "fieldname": "forwarding_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Clearing", "fieldname": "clearing_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Trucking", "fieldname": "trucking_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Road Freight", "fieldname": "road_freight_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Total Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 140},
		{"label": "Services Used", "fieldname": "service_count", "fieldtype": "Int", "width": 110},
	]
