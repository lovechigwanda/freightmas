# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""Return columns for the report"""
	return [
		{
			"fieldname": "movement_date",
			"label": _("Movement Date"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "name",
			"label": _("Movement #"),
			"fieldtype": "Link",
			"options": "Goods Movement",
			"width": 150
		},
		{
			"fieldname": "movement_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "goods_receipt",
			"label": _("Goods Receipt"),
			"fieldtype": "Link",
			"options": "Customer Goods Receipt",
			"width": 150
		},
		{
			"fieldname": "source_zone",
			"label": _("Source Zone"),
			"fieldtype": "Link",
			"options": "Warehouse Zone",
			"width": 120
		},
		{
			"fieldname": "source_bin",
			"label": _("Source Bin"),
			"fieldtype": "Link",
			"options": "Warehouse Bin",
			"width": 120
		},
		{
			"fieldname": "destination_zone",
			"label": _("Destination Zone"),
			"fieldtype": "Link",
			"options": "Warehouse Zone",
			"width": 120
		},
		{
			"fieldname": "destination_bin",
			"label": _("Destination Bin"),
			"fieldtype": "Link",
			"options": "Warehouse Bin",
			"width": 120
		},
		{
			"fieldname": "moved_by",
			"label": _("Moved By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 120
		},
		{
			"fieldname": "reason",
			"label": _("Reason"),
			"fieldtype": "Data",
			"width": 150
		}
	]


def get_data(filters):
	"""Get data for the report"""
	conditions = get_conditions(filters)
	
	data = frappe.db.sql(f"""
		SELECT
			gm.movement_date,
			gm.name,
			gm.movement_type,
			gm.customer,
			gm.goods_receipt,
			gm.source_zone,
			gm.source_bin,
			gm.destination_zone,
			gm.destination_bin,
			gm.moved_by,
			gm.reason
		FROM
			`tabGoods Movement` gm
		WHERE
			gm.docstatus = 1
			{conditions}
		ORDER BY
			gm.movement_date DESC
	""", filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""Build WHERE conditions from filters"""
	conditions = ""
	
	if filters.get("customer"):
		conditions += " AND gm.customer = %(customer)s"
	
	if filters.get("movement_type"):
		conditions += " AND gm.movement_type = %(movement_type)s"
	
	if filters.get("from_date"):
		conditions += " AND DATE(gm.movement_date) >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND DATE(gm.movement_date) <= %(to_date)s"
	
	if filters.get("warehouse_zone"):
		conditions += " AND (gm.source_zone = %(warehouse_zone)s OR gm.destination_zone = %(warehouse_zone)s)"
	
	return conditions
