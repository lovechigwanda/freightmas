# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate, date_diff


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_data(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if not from_date or not to_date:
		return []

	period_days = date_diff(to_date, from_date) + 1
	if period_days <= 0:
		return []

	conditions = ["t.docstatus < 2"]
	params = {"from_date": from_date, "to_date": to_date}

	conditions.append("t.date_created <= %(to_date)s")
	# Include trips that overlap with the period
	conditions.append("""(
		t.date_created >= %(from_date)s
		OR (t.date_loaded IS NOT NULL AND t.date_loaded <= %(to_date)s)
	)""")

	if filters.get("truck"):
		conditions.append("t.truck = %(truck)s")
		params["truck"] = filters["truck"]

	if filters.get("company"):
		conditions.append("t.company = %(company)s")
		params["company"] = filters["company"]

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql("""
		SELECT
			t.truck,
			COUNT(t.name) as trip_count,
			COUNT(DISTINCT t.date_loaded) as active_days,
			SUM(IFNULL(t.total_estimated_revenue, 0)) as total_revenue,
			AVG(CASE
				WHEN t.date_offloaded IS NOT NULL AND t.date_loaded IS NOT NULL
				THEN DATEDIFF(t.date_offloaded, t.date_loaded)
			END) as avg_turnaround
		FROM `tabTrip` t
		WHERE {where_clause}
		GROUP BY t.truck
		ORDER BY trip_count DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	data = []
	for row in rows:
		active_days = row.active_days or 0
		idle_days = max(period_days - active_days, 0)
		utilisation_pct = (active_days / period_days * 100) if period_days else 0
		revenue = flt(row.total_revenue)
		rev_per_available_day = (revenue / period_days) if period_days else 0
		rev_per_active_day = (revenue / active_days) if active_days else 0

		data.append({
			"truck": row.truck,
			"period_days": period_days,
			"trip_count": row.trip_count,
			"active_days": active_days,
			"idle_days": idle_days,
			"utilisation_percent": flt(utilisation_pct, 1),
			"total_revenue": flt(revenue, 2),
			"revenue_per_available_day": flt(rev_per_available_day, 2),
			"revenue_per_active_day": flt(rev_per_active_day, 2),
			"avg_turnaround": flt(row.avg_turnaround, 1),
		})

	return data


def get_columns():
	return [
		{"label": "Truck", "fieldname": "truck", "fieldtype": "Link", "options": "Truck", "width": 110},
		{"label": "Period Days", "fieldname": "period_days", "fieldtype": "Int", "width": 100},
		{"label": "Trips", "fieldname": "trip_count", "fieldtype": "Int", "width": 70},
		{"label": "Active Days", "fieldname": "active_days", "fieldtype": "Int", "width": 100},
		{"label": "Idle Days", "fieldname": "idle_days", "fieldtype": "Int", "width": 90},
		{"label": "Utilisation %", "fieldname": "utilisation_percent", "fieldtype": "Percent", "width": 110},
		{"label": "Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 120},
		{"label": "Rev/Available Day", "fieldname": "revenue_per_available_day", "fieldtype": "Currency", "width": 140},
		{"label": "Rev/Active Day", "fieldname": "revenue_per_active_day", "fieldtype": "Currency", "width": 130},
		{"label": "Avg Turnaround", "fieldname": "avg_turnaround", "fieldtype": "Float", "width": 120},
	]
