# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, formatdate, now_datetime, date_diff


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data, summary = get_data(filters)
	return columns, data, None, None, summary


def get_columns():
	return [
		{"label": "Job", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 160},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 160},
		{"label": "Tracking Status", "fieldname": "api_tracking_status", "fieldtype": "Data", "width": 130},
		{"label": "Last Event", "fieldname": "api_last_event", "fieldtype": "Data", "width": 220},
		{"label": "Last Event Date", "fieldname": "api_last_event_date", "fieldtype": "Date", "width": 120},
		{"label": "Last Fetched", "fieldname": "api_last_fetched", "fieldtype": "Datetime", "width": 160},
		{"label": "Days Since Fetch", "fieldname": "days_since_fetch", "fieldtype": "Int", "width": 120},
		{"label": "Job Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 100},
		{"label": "Shipment Mode", "fieldname": "shipment_mode", "fieldtype": "Data", "width": 110},
		{"label": "API Calls", "fieldname": "api_call_count", "fieldtype": "Int", "width": 90},
		{"label": "Date Created", "fieldname": "date_created", "fieldtype": "Date", "width": 110},
	]


def get_data(filters):
	conditions = ["fj.enable_api_tracking = 1", "fj.docstatus < 2"]
	params = {}

	if filters.get("from_date"):
		conditions.append("fj.date_created >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("fj.date_created <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("customer"):
		conditions.append("fj.customer = %(customer)s")
		params["customer"] = filters["customer"]

	if filters.get("tracking_status"):
		ts = filters["tracking_status"]
		if ts == "Never Fetched":
			conditions.append("(fj.api_last_fetched IS NULL OR fj.api_last_fetched = '')")
		else:
			conditions.append("fj.api_tracking_status = %(tracking_status)s")
			params["tracking_status"] = ts

	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql(
		"""
		SELECT
			fj.name, fj.customer, fj.bl_number,
			fj.api_tracking_status, fj.api_last_event,
			fj.api_last_event_date, fj.api_last_fetched,
			fj.status, fj.direction, fj.shipment_mode,
			fj.api_call_count, fj.date_created
		FROM `tabForwarding Job` fj
		WHERE {where_clause}
		ORDER BY fj.api_last_fetched DESC, fj.date_created DESC
		""".format(where_clause=where_clause),
		params,
		as_dict=True,
	)

	today = getdate()
	total = len(rows)
	active = 0
	delivered = 0
	never_fetched = 0
	total_api_calls = 0

	for row in rows:
		total_api_calls += row.get("api_call_count") or 0

		# Calculate days since last fetch
		if row.get("api_last_fetched"):
			row["days_since_fetch"] = date_diff(today, getdate(row["api_last_fetched"]))
		else:
			row["days_since_fetch"] = None
			never_fetched += 1

		status = (row.get("api_tracking_status") or "").upper()
		if status in ("DELIVERED", "ARRIVED"):
			delivered += 1
		elif row.get("api_last_fetched"):
			active += 1

	summary = [
		{"value": total, "indicator": "Blue", "label": "Total Tracked Jobs", "datatype": "Int"},
		{"value": active, "indicator": "Orange", "label": "Active (In Transit)", "datatype": "Int"},
		{"value": delivered, "indicator": "Green", "label": "Delivered / Arrived", "datatype": "Int"},
		{"value": never_fetched, "indicator": "Red", "label": "Never Fetched", "datatype": "Int"},
		{"value": total_api_calls, "indicator": "Purple", "label": "Total API Calls", "datatype": "Int"},
	]

	return rows, summary
