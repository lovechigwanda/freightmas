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
	conditions = ["t.docstatus < 2"]
	params = {}

	if filters.get("from_date"):
		conditions.append("t.date_created >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("t.date_created <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("truck"):
		conditions.append("t.truck = %(truck)s")
		params["truck"] = filters["truck"]

	if filters.get("company"):
		conditions.append("t.company = %(company)s")
		params["company"] = filters["company"]

	where_clause = " AND ".join(conditions)

	# Fuel costs per truck
	fuel_data = frappe.db.sql("""
		SELECT t.truck, 'Fuel' as expense_type, SUM(IFNULL(fa.amount, 0)) as amount
		FROM `tabTrip Fuel Allocation` fa
		INNER JOIN `tabTrip` t ON fa.parent = t.name
		WHERE {where_clause}
		GROUP BY t.truck
	""".format(where_clause=where_clause), params, as_dict=True)

	# Other costs per truck broken down by item
	other_data = frappe.db.sql("""
		SELECT t.truck,
			IFNULL(oc.item_name, IFNULL(oc.description, 'Other')) as expense_type,
			SUM(IFNULL(oc.total_amount, 0)) as amount
		FROM `tabTrip Other Costs` oc
		INNER JOIN `tabTrip` t ON oc.parent = t.name
		WHERE {where_clause}
		GROUP BY t.truck, expense_type
	""".format(where_clause=where_clause), params, as_dict=True)

	# Revenue per truck for context
	revenue_data = {}
	rev_rows = frappe.db.sql("""
		SELECT t.truck, SUM(IFNULL(t.total_estimated_revenue, 0)) as revenue
		FROM `tabTrip` t
		WHERE {where_clause}
		GROUP BY t.truck
	""".format(where_clause=where_clause), params, as_dict=True)
	for r in rev_rows:
		revenue_data[r.truck] = flt(r.revenue)

	# Combine all expenses
	truck_expenses = {}
	for row in fuel_data + other_data:
		if row.truck not in truck_expenses:
			truck_expenses[row.truck] = {}
		truck_expenses[row.truck][row.expense_type] = flt(row.amount)

	data = []
	for truck, expenses in sorted(truck_expenses.items()):
		total_expense = sum(expenses.values())
		truck_revenue = revenue_data.get(truck, 0)
		for expense_type, amount in sorted(expenses.items(), key=lambda x: -x[1]):
			pct_of_total = (amount / total_expense * 100) if total_expense else 0
			pct_of_revenue = (amount / truck_revenue * 100) if truck_revenue else 0
			data.append({
				"truck": truck,
				"expense_type": expense_type,
				"amount": flt(amount, 2),
				"percent_of_total_cost": flt(pct_of_total, 1),
				"percent_of_revenue": flt(pct_of_revenue, 1),
				"truck_revenue": flt(truck_revenue, 2),
				"total_truck_cost": flt(total_expense, 2),
			})

	return data


def get_columns():
	return [
		{"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 110},
		{"label": "Expense Type", "fieldname": "expense_type", "fieldtype": "Data", "width": 180},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": "% of Cost", "fieldname": "percent_of_total_cost", "fieldtype": "Percent", "width": 100},
		{"label": "% of Revenue", "fieldname": "percent_of_revenue", "fieldtype": "Percent", "width": 110},
		{"label": "Truck Revenue", "fieldname": "truck_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Total Truck Cost", "fieldname": "total_truck_cost", "fieldtype": "Currency", "width": 130},
	]
