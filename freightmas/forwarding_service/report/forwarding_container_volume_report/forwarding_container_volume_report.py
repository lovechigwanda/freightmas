# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate
import calendar


TEU_MAP = {
	"20ft": 1, "20GP": 1, "20RF": 1, "20OT": 1, "20FR": 1,
	"40ft": 2, "40GP": 2, "40HC": 2, "40RF": 2, "40OT": 2, "40FR": 2,
	"45ft": 2.25, "45HC": 2.25,
}


def _get_teu(container_type):
	if not container_type:
		return 1
	ct = container_type.strip()
	for key, val in TEU_MAP.items():
		if key.lower() in ct.lower():
			return val
	return 1


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_data(filters):
	conditions = ["fj.docstatus < 2"]
	params = {}

	if filters.get("from_date"):
		conditions.append("fj.date_created >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("fj.date_created <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("direction"):
		conditions.append("fj.direction = %(direction)s")
		params["direction"] = filters["direction"]

	if filters.get("shipment_mode"):
		conditions.append("fj.shipment_mode = %(shipment_mode)s")
		params["shipment_mode"] = filters["shipment_mode"]

	if filters.get("company"):
		conditions.append("fj.company = %(company)s")
		params["company"] = filters["company"]

	where_clause = " AND ".join(conditions)

	parcels = frappe.db.sql("""
		SELECT
			MONTH(fj.date_created) as month_num,
			YEAR(fj.date_created) as year_num,
			fj.direction,
			fj.shipment_mode,
			cpd.container_type,
			COUNT(cpd.name) as container_count
		FROM `tabCargo Parcel Details` cpd
		INNER JOIN `tabForwarding Job` fj ON cpd.parent = fj.name
		WHERE {where_clause}
		GROUP BY year_num, month_num, fj.direction, fj.shipment_mode, cpd.container_type
		ORDER BY year_num, month_num, fj.direction
	""".format(where_clause=where_clause), params, as_dict=True)

	data = []
	for row in parcels:
		teu = _get_teu(row.container_type) * row.container_count
		month_name = calendar.month_abbr[row.month_num] if row.month_num else ""
		data.append({
			"period": f"{month_name} {row.year_num}",
			"direction": row.direction,
			"shipment_mode": row.shipment_mode,
			"container_type": row.container_type,
			"container_count": row.container_count,
			"teu": flt(teu, 2),
		})

	return data


def get_columns():
	return [
		{"label": "Period", "fieldname": "period", "fieldtype": "Data", "width": 110},
		{"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 100},
		{"label": "Shipment Mode", "fieldname": "shipment_mode", "fieldtype": "Data", "width": 120},
		{"label": "Container Type", "fieldname": "container_type", "fieldtype": "Data", "width": 130},
		{"label": "Containers", "fieldname": "container_count", "fieldtype": "Int", "width": 100},
		{"label": "TEU", "fieldname": "teu", "fieldtype": "Float", "width": 90},
	]
