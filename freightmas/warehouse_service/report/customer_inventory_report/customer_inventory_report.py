# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, date_diff, today


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""Return columns for the report"""
	return [
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "goods_receipt",
			"label": _("Goods Receipt #"),
			"fieldtype": "Link",
			"options": "Customer Goods Receipt",
			"width": 150
		},
		{
			"fieldname": "receipt_date",
			"label": _("Receipt Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100
		},
		{
			"fieldname": "quantity_in",
			"label": _("Quantity In"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "quantity_dispatched",
			"label": _("Quantity Dispatched"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "quantity_remaining",
			"label": _("Quantity Remaining"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "warehouse_bin",
			"label": _("Bin"),
			"fieldtype": "Link",
			"options": "Warehouse Bin",
			"width": 120
		},
		{
			"fieldname": "days_in_storage",
			"label": _("Days in Storage"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters):
	"""Get data for the report"""
	conditions = get_conditions(filters)
	
	data = frappe.db.sql(f"""
		SELECT
			cgr.customer,
			cgr.name as goods_receipt,
			cgr.receipt_date,
			cgri.description,
		cgri.stock_uom as uom,
		cgri.actual_stock_quantity as quantity_in,
		(cgri.actual_stock_quantity - cgri.quantity_remaining) as quantity_dispatched,
			cgri.quantity_remaining,
			cgri.warehouse_bin,
			DATEDIFF(CURDATE(), cgr.receipt_date) as days_in_storage,
			cgri.status
		FROM
			`tabCustomer Goods Receipt` cgr
		INNER JOIN
			`tabCustomer Goods Receipt Item` cgri ON cgri.parent = cgr.name
		WHERE
			cgr.docstatus = 1
			AND cgri.quantity_remaining > 0
			{conditions}
		ORDER BY
			cgr.customer, cgr.receipt_date
	""", filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""Build WHERE conditions from filters"""
	conditions = ""
	
	if filters.get("customer"):
		conditions += " AND cgr.customer = %(customer)s"
	
	if filters.get("from_date"):
		conditions += " AND cgr.receipt_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND cgr.receipt_date <= %(to_date)s"
	
	if filters.get("status"):
		conditions += " AND cgri.status = %(status)s"
	
	return conditions
