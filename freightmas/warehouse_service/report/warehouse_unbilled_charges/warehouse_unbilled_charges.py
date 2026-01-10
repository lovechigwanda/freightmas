# Copyright (c) 2026, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = []

	# Get unbilled handling charges
	if not filters.get("charge_type") or filters.get("charge_type") in ["", "Handling", "Both"]:
		handling_data = get_handling_charges(filters)
		data.extend(handling_data)

	# Get unbilled storage charges
	if not filters.get("charge_type") or filters.get("charge_type") in ["", "Storage", "Both"]:
		storage_data = get_storage_charges(filters)
		data.extend(storage_data)

	# Sort by customer and warehouse job (handle None values)
	data = sorted(data, key=lambda x: (x.get("customer") or "", x.get("warehouse_job") or ""))

	return columns, data


def get_handling_charges(filters):
	"""Get unbilled handling charges"""
	conditions = ["hc.is_invoiced = 0"]
	params = {}
	
	if filters.get("customer"):
		conditions.append("hc.customer = %(customer)s")
		params["customer"] = filters["customer"]
	if filters.get("warehouse_job"):
		conditions.append("hc.parent = %(warehouse_job)s")
		params["warehouse_job"] = filters["warehouse_job"]

	where_clause = " AND ".join(conditions)

	charges = frappe.db.sql("""
		SELECT 
			hc.parent as warehouse_job,
			hc.customer,
			wj.reference_number,
			hc.activity_date,
			hc.handling_activity_type,
			hc.description,
			hc.quantity,
			hc.rate,
			hc.amount,
			'Handling' as charge_type
		FROM `tabWarehouse Job Handling Charges` hc
		INNER JOIN `tabWarehouse Job` wj ON hc.parent = wj.name
		WHERE {where_clause}
		ORDER BY hc.activity_date DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	data = []
	for charge in charges:
		data.append({
			"warehouse_job": charge.get("warehouse_job", ""),
			"customer": charge.get("customer", ""),
			"reference_number": charge.get("reference_number", ""),
			"charge_type": "Handling",
			"date": format_date(charge.get("activity_date")),
			"description": f"{charge.get('handling_activity_type', '')} - {charge.get('description', '')}".strip(" - "),
			"quantity": charge.get("quantity", 0),
			"rate": charge.get("rate", 0),
			"amount": charge.get("amount", 0),
		})

	return data


def get_storage_charges(filters):
	"""Get unbilled storage charges"""
	conditions = ["sc.is_invoiced = 0"]
	params = {}
	
	if filters.get("customer"):
		conditions.append("wj.customer = %(customer)s")
		params["customer"] = filters["customer"]
	if filters.get("warehouse_job"):
		conditions.append("sc.parent = %(warehouse_job)s")
		params["warehouse_job"] = filters["warehouse_job"]

	where_clause = " AND ".join(conditions)

	charges = frappe.db.sql("""
		SELECT 
			sc.parent as warehouse_job,
			wj.customer,
			wj.reference_number,
			sc.end_date,
			sc.uom,
			sc.quantity,
			sc.start_date,
			sc.storage_days,
			sc.amount
		FROM `tabWarehouse Job Storage Charges` sc
		INNER JOIN `tabWarehouse Job` wj ON sc.parent = wj.name
		WHERE {where_clause}
		ORDER BY sc.end_date DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	data = []
	for charge in charges:
		# Calculate rate per day
		rate = 0
		if charge.get("storage_days") and charge.get("quantity"):
			rate = flt(charge.get("amount", 0)) / (flt(charge.get("storage_days")) * flt(charge.get("quantity")))

		data.append({
			"warehouse_job": charge.get("warehouse_job", ""),
			"customer": charge.get("customer", ""),
			"reference_number": charge.get("reference_number", ""),
			"charge_type": "Storage",
			"date": format_date(charge.get("end_date")),
			"description": f"Storage: {charge.get('uom', '')} ({charge.get('storage_days', 0)} days)",
			"quantity": charge.get("quantity", 0),
			"rate": rate,
			"amount": charge.get("amount", 0),
		})

	return data


def get_columns():
	return [
		{"label": "Warehouse Job", "fieldname": "warehouse_job", "fieldtype": "Link", "options": "Warehouse Job", "width": 150},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": "Reference", "fieldname": "reference_number", "fieldtype": "Data", "width": 120},
		{"label": "Type", "fieldname": "charge_type", "fieldtype": "Data", "width": 90},
		{"label": "Date", "fieldname": "date", "fieldtype": "Data", "width": 100},
		{"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 250},
		{"label": "Quantity", "fieldname": "quantity", "fieldtype": "Float", "width": 90},
		{"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 100},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]


def format_date(date_str):
	"""Format date string to dd-MMM-yy format."""
	if not date_str:
		return ""
	try:
		return formatdate(date_str, "dd-MMM-yy")
	except Exception:
		return date_str
