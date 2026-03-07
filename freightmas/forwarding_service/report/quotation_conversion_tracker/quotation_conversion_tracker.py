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
		"q.custom_job_order_reference IS NOT NULL",
		"q.custom_job_order_reference != ''",
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

	if filters.get("conversion_status"):
		if filters["conversion_status"] == "JO Only":
			conditions.append(
				"(jo.forwarding_job_reference IS NULL OR jo.forwarding_job_reference = '')"
			)
		elif filters["conversion_status"] == "Fully Converted":
			conditions.append("jo.forwarding_job_reference IS NOT NULL")
			conditions.append("jo.forwarding_job_reference != ''")

	where_clause = " AND ".join(conditions)

	results = frappe.db.sql(
		"""
		SELECT
			q.name AS quotation_no,
			q.transaction_date,
			q.party_name AS customer,
			q.customer_reference,
			q.grand_total,
			jo.name AS job_order_no,
			jo.forwarding_job_reference AS forwarding_job_no
		FROM `tabQuotation` q
		LEFT JOIN `tabJob Order` jo
			ON jo.name = q.custom_job_order_reference
		WHERE {where_clause}
		ORDER BY q.transaction_date DESC
	""".format(
			where_clause=where_clause
		),
		params,
		as_dict=True,
	)

	for row in results:
		conversion_status = "JO Only"
		if row.get("forwarding_job_no"):
			conversion_status = "Fully Converted"

		data.append(
			{
				"quotation_no": row.quotation_no,
				"quotation_date": format_date(row.transaction_date),
				"customer": row.get("customer", ""),
				"customer_reference": row.get("customer_reference", ""),
				"grand_total": row.get("grand_total", 0),
				"job_order_no": row.get("job_order_no", ""),
				"forwarding_job_no": row.get("forwarding_job_no", ""),
				"conversion_status": conversion_status,
			}
		)

	return data


def get_columns():
	return [
		{"label": "Quotation", "fieldname": "quotation_no", "fieldtype": "Link", "options": "Quotation", "width": 150},
		{"label": "Quotation Date", "fieldname": "quotation_date", "fieldtype": "Data", "width": 110},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": "Customer Ref", "fieldname": "customer_reference", "fieldtype": "Data", "width": 130},
		{"label": "Quoted Amount", "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
		{"label": "Job Order", "fieldname": "job_order_no", "fieldtype": "Link", "options": "Job Order", "width": 150},
		{"label": "Forwarding Job", "fieldname": "forwarding_job_no", "fieldtype": "Link", "options": "Forwarding Job", "width": 150},
		{"label": "Conversion", "fieldname": "conversion_status", "fieldtype": "Data", "width": 120},
	]


def format_date(date_str):
	"""Format date string to dd-MMM-yy format."""
	if not date_str:
		return ""
	try:
		return formatdate(date_str, "dd-MMM-yy")
	except Exception:
		return date_str
