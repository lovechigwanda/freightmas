# Copyright (c) 2026, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = []

	conditions = "1=1"
	if filters.get("from_date"):
		conditions += f" AND sc.start_date >= '{filters['from_date']}'"
	if filters.get("to_date"):
		conditions += f" AND sc.end_date <= '{filters['to_date']}'"
	if filters.get("customer"):
		conditions += f" AND wj.customer = '{filters['customer']}'"
	if filters.get("warehouse_job"):
		conditions += f" AND sc.parent = '{filters['warehouse_job']}'"
	if filters.get("uom"):
		conditions += f" AND sc.uom = '{filters['uom']}'"
	if filters.get("invoiced_status"):
		if filters["invoiced_status"] == "Invoiced":
			conditions += " AND sc.is_invoiced = 1"
		elif filters["invoiced_status"] == "Uninvoiced":
			conditions += " AND sc.is_invoiced = 0"

	charges = frappe.db.sql(f"""
		SELECT 
			sc.name,
			sc.parent as warehouse_job,
			wj.customer,
			wj.reference_number,
			sc.uom,
			sc.quantity,
			sc.start_date,
			sc.end_date,
			sc.storage_days,
			sc.amount,
			sc.is_invoiced
		FROM `tabWarehouse Job Storage Charges` sc
		INNER JOIN `tabWarehouse Job` wj ON sc.parent = wj.name
		WHERE {conditions}
		ORDER BY sc.start_date DESC, wj.customer
	""", as_dict=True)

	for charge in charges:
		# Calculate rate per day
		rate_per_day = 0
		if charge.get("storage_days") and charge.get("quantity"):
			rate_per_day = flt(charge.get("amount", 0)) / (flt(charge.get("storage_days")) * flt(charge.get("quantity")))

		data.append({
			"warehouse_job": charge.get("warehouse_job", ""),
			"customer": charge.get("customer", ""),
			"reference_number": charge.get("reference_number", ""),
			"uom": charge.get("uom", ""),
			"quantity": charge.get("quantity", 0),
			"start_date": format_date(charge.get("start_date")),
			"end_date": format_date(charge.get("end_date")),
			"storage_days": charge.get("storage_days", 0),
			"rate_per_day": rate_per_day,
			"amount": charge.get("amount", 0),
			"is_invoiced": "Yes" if charge.get("is_invoiced") else "No",
		})

	return columns, data


def get_columns():
	return [
		{"label": "Warehouse Job", "fieldname": "warehouse_job", "fieldtype": "Link", "options": "Warehouse Job", "width": 150},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": "Reference", "fieldname": "reference_number", "fieldtype": "Data", "width": 120},
		{"label": "UOM", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": "Quantity", "fieldname": "quantity", "fieldtype": "Float", "width": 90},
		{"label": "Start Date", "fieldname": "start_date", "fieldtype": "Data", "width": 100},
		{"label": "End Date", "fieldname": "end_date", "fieldtype": "Data", "width": 100},
		{"label": "Days", "fieldname": "storage_days", "fieldtype": "Int", "width": 70},
		{"label": "Rate/Day", "fieldname": "rate_per_day", "fieldtype": "Currency", "width": 100},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": "Invoiced", "fieldname": "is_invoiced", "fieldtype": "Data", "width": 90},
	]


def format_date(date_str):
	"""Format date string to dd-MMM-yy format."""
	if not date_str:
		return ""
	try:
		return formatdate(date_str, "dd-MMM-yy")
	except Exception:
		return date_str
