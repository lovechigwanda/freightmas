# Copyright (c) 2026, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, flt, getdate, today


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = []

	conditions = ["cgri.quantity_remaining > 0", "cgr.docstatus = 1"]
	params = {}
	
	if filters.get("customer"):
		conditions.append("cgr.customer = %(customer)s")
		params["customer"] = filters["customer"]
	if filters.get("warehouse_job"):
		conditions.append("cgr.warehouse_job = %(warehouse_job)s")
		params["warehouse_job"] = filters["warehouse_job"]
	if filters.get("uom"):
		conditions.append("cgri.stock_uom = %(uom)s")
		params["uom"] = filters["uom"]
	if filters.get("warehouse_bay"):
		conditions.append("cgri.warehouse_bay = %(warehouse_bay)s")
		params["warehouse_bay"] = filters["warehouse_bay"]

	where_clause = " AND ".join(conditions)

	items = frappe.db.sql("""
		SELECT 
			cgr.warehouse_job,
			cgr.customer,
			cgr.name as receipt_number,
			cgr.receipt_date,
			cgri.storage_unit_item,
			cgri.customer_reference,
			cgri.description,
			cgri.stock_uom as uom,
			cgri.actual_stock_quantity as quantity,
			cgri.quantity_remaining,
			cgri.warehouse_bay,
			cgri.warehouse_bin,
			cgri.status
		FROM `tabCustomer Goods Receipt Item` cgri
		INNER JOIN `tabCustomer Goods Receipt` cgr ON cgri.parent = cgr.name
		WHERE {where_clause}
		ORDER BY cgr.customer, cgr.warehouse_job, cgri.warehouse_bay, cgri.warehouse_bin
	""".format(where_clause=where_clause), params, as_dict=True)

	for item in items:
		# Calculate days in warehouse
		receipt_date = getdate(item.get("receipt_date"))
		today_date = getdate(today())
		days_in_warehouse = (today_date - receipt_date).days

		# Get storage rate for this UOM from the warehouse job
		storage_rate = get_storage_rate(item.get("warehouse_job"), item.get("uom"))

		data.append({
			"warehouse_job": item.get("warehouse_job", ""),
			"customer": item.get("customer", ""),
			"receipt_number": item.get("receipt_number", ""),
			"receipt_date": format_date(item.get("receipt_date")),
			"storage_unit_item": item.get("storage_unit_item", ""),
			"customer_reference": item.get("customer_reference", ""),
			"description": item.get("description", ""),
			"uom": item.get("uom", ""),
			"quantity_received": item.get("quantity", 0),
			"quantity_remaining": item.get("quantity_remaining", 0),
			"quantity_dispatched": flt(item.get("quantity", 0)) - flt(item.get("quantity_remaining", 0)),
			"warehouse_bay": item.get("warehouse_bay", ""),
			"warehouse_bin": item.get("warehouse_bin", ""),
			"days_in_warehouse": days_in_warehouse,
			"storage_rate_per_day": storage_rate,
			"status": item.get("status", ""),
		})

	return columns, data


def get_storage_rate(warehouse_job, uom):
	"""Get storage rate per day for a specific UOM from warehouse job"""
	if not warehouse_job or not uom:
		return 0
	
	rate = frappe.db.get_value(
		"Storage Rate Item",
		{"parent": warehouse_job, "uom": uom},
		"rate_per_day"
	)
	
	return flt(rate)


def get_columns():
	return [
		{"label": "Warehouse Job", "fieldname": "warehouse_job", "fieldtype": "Link", "options": "Warehouse Job", "width": 150},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": "Receipt #", "fieldname": "receipt_number", "fieldtype": "Link", "options": "Customer Goods Receipt", "width": 140},
		{"label": "Receipt Date", "fieldname": "receipt_date", "fieldtype": "Data", "width": 100},
		{"label": "Item Code", "fieldname": "storage_unit_item", "fieldtype": "Data", "width": 100},
		{"label": "Customer Ref", "fieldname": "customer_reference", "fieldtype": "Data", "width": 110},
		{"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 180},
		{"label": "UOM", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 70},
		{"label": "Qty Received", "fieldname": "quantity_received", "fieldtype": "Float", "width": 100},
		{"label": "Qty Remaining", "fieldname": "quantity_remaining", "fieldtype": "Float", "width": 110},
		{"label": "Qty Dispatched", "fieldname": "quantity_dispatched", "fieldtype": "Float", "width": 110},
		{"label": "Bay", "fieldname": "warehouse_bay", "fieldtype": "Link", "options": "Warehouse Bay", "width": 80},
		{"label": "Bin", "fieldname": "warehouse_bin", "fieldtype": "Link", "options": "Warehouse Bin", "width": 80},
		{"label": "Days in WH", "fieldname": "days_in_warehouse", "fieldtype": "Int", "width": 90},
		{"label": "Rate/Day", "fieldname": "storage_rate_per_day", "fieldtype": "Currency", "width": 90},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
	]


def format_date(date_str):
	"""Format date string to dd-MMM-yy format."""
	if not date_str:
		return ""
	try:
		return formatdate(date_str, "dd-MMM-yy")
	except Exception:
		return date_str
