# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_data(filters):
	data = []

	conditions = [
		"q.is_freight_quote = 1",
		"q.docstatus < 2",
		"(q.custom_job_order_reference IS NULL OR q.custom_job_order_reference = '')",
		"q.workflow_state NOT IN ('JO Created', 'Cancelled')",
	]
	params = {}

	if filters.get("from_date"):
		conditions.append("q.transaction_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("q.transaction_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("customer"):
		conditions.append("q.party_name = %(customer)s")
		params["customer"] = filters["customer"]

	if filters.get("workflow_state"):
		conditions.append("q.workflow_state = %(workflow_state)s")
		params["workflow_state"] = filters["workflow_state"]

	where_clause = " AND ".join(conditions)

	results = frappe.db.sql(
		"""
		SELECT
			q.name AS quotation_no,
			q.transaction_date,
			q.party_name AS customer,
			q.customer_reference,
			q.grand_total,
			q.valid_till,
			DATEDIFF(CURDATE(), q.transaction_date) AS age_days,
			q.workflow_state
		FROM `tabQuotation` q
		WHERE {where_clause}
		ORDER BY q.transaction_date DESC
	""".format(
			where_clause=where_clause
		),
		params,
		as_dict=True,
	)

	for row in results:
		data.append(
			{
				"quotation_no": row.quotation_no,
				"quotation_date": format_date(row.transaction_date),
				"customer": row.get("customer", ""),
				"customer_reference": row.get("customer_reference", ""),
				"grand_total": row.get("grand_total", 0),
				"valid_till": format_date(row.get("valid_till")),
				"age_days": row.get("age_days", 0),
				"workflow_state": row.get("workflow_state", ""),
			}
		)

	return data


def get_columns():
	return [
		{"label": "Quotation", "fieldname": "quotation_no", "fieldtype": "Link", "options": "Quotation", "width": 150},
		{"label": "Date", "fieldname": "quotation_date", "fieldtype": "Data", "width": 110},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": "Customer Ref", "fieldname": "customer_reference", "fieldtype": "Data", "width": 130},
		{"label": "Grand Total", "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
		{"label": "Valid Till", "fieldname": "valid_till", "fieldtype": "Data", "width": 110},
		{"label": "Age (Days)", "fieldname": "age_days", "fieldtype": "Int", "width": 90},
		{"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 130},
	]


def format_date(date_str):
	"""Format date string to dd-MMM-yy format."""
	if not date_str:
		return ""
	try:
		return formatdate(date_str, "dd-MMM-yy")
	except Exception:
		return date_str
