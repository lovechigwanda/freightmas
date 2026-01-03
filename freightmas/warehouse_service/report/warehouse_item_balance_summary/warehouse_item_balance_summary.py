# Copyright (c) 2026, Codes Soft and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 200
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 80
		},
		{
			"fieldname": "total_quantity",
			"label": _("Total Quantity"),
			"fieldtype": "Float",
			"width": 120,
			"precision": 2
		},
		{
			"fieldname": "avg_days_in_warehouse",
			"label": _("Avg Days in Warehouse"),
			"fieldtype": "Int",
			"width": 150
		},
		{
			"fieldname": "receipt_count",
			"label": _("Number of Receipts"),
			"fieldtype": "Int",
			"width": 140
		},
		{
			"fieldname": "warehouses_count",
			"label": _("Bay Locations"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "bins_count",
			"label": _("Bin Locations"),
			"fieldtype": "Int",
			"width": 120
		}
	]


def get_data(filters):
	"""Get summarized item balance data"""
	conditions = get_conditions(filters)
	
	# Query to get all items in warehouse with their details
	query = """
		SELECT
			wj.customer,
			cgri.storage_unit_item as item_code,
			cgri.description as item_name,
			cgri.uom,
			SUM(cgri.quantity_remaining) as total_quantity,
			AVG(DATEDIFF(CURDATE(), cgr.receipt_date)) as avg_days_in_warehouse,
			COUNT(DISTINCT cgri.warehouse_bay) as warehouses_count,
			COUNT(DISTINCT cgri.warehouse_bin) as bins_count,
			COUNT(DISTINCT cgri.parent) as receipt_count
		FROM
			`tabCustomer Goods Receipt Item` cgri
		INNER JOIN
			`tabCustomer Goods Receipt` cgr ON cgr.name = cgri.parent
		INNER JOIN
			`tabWarehouse Job` wj ON wj.name = cgr.warehouse_job
		WHERE
			cgr.docstatus = 1
			AND wj.status != 'Closed'
			{conditions}
		GROUP BY
			wj.customer, cgri.storage_unit_item, cgri.description, cgri.uom
		HAVING
			total_quantity > 0 OR {show_zero}
		ORDER BY
			wj.customer, cgri.storage_unit_item
	""".format(
		conditions=conditions,
		show_zero="1=1" if cint(filters.get("show_zero_balance")) else "1=0"
	)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Process data
	for row in data:
		row["total_quantity"] = flt(row.get("total_quantity"), 2)
		row["avg_days_in_warehouse"] = cint(row.get("avg_days_in_warehouse"))
		row["warehouses_count"] = cint(row.get("warehouses_count"))
		row["bins_count"] = cint(row.get("bins_count"))
		row["receipt_count"] = cint(row.get("receipt_count"))
	
	return data


def get_conditions(filters):
	"""Build SQL conditions based on filters"""
	conditions = []
	
	if filters.get("customer"):
		conditions.append("wj.customer = %(customer)s")
	
	if filters.get("item_code"):
		conditions.append("cgri.storage_unit_item LIKE CONCAT('%%', %(item_code)s, '%%')")
	
	if filters.get("item_name"):
		conditions.append("cgri.description LIKE CONCAT('%%', %(item_name)s, '%%')")
	
	return " AND " + " AND ".join(conditions) if conditions else ""
