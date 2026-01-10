# Copyright (c) 2026, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = []

	conditions = ["1=1"]
	params = {}
	
	if filters.get("from_date"):
		conditions.append("job_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("job_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	if filters.get("customer"):
		conditions.append("customer = %(customer)s")
		params["customer"] = filters["customer"]
	if filters.get("status"):
		conditions.append("status = %(status)s")
		params["status"] = filters["status"]
	if filters.get("job_type"):
		conditions.append("job_type = %(job_type)s")
		params["job_type"] = filters["job_type"]

	where_clause = " AND ".join(conditions)

	jobs = frappe.db.sql("""
		SELECT 
			name, job_date, customer, reference_number,
			job_type, contract_type, fiscal_year,
			job_start_date, job_end_date, status,
			total_handling_charges, total_storage_charges,
			invoiced_amount
		FROM `tabWarehouse Job`
		WHERE {where_clause}
		ORDER BY job_date DESC
	""".format(where_clause=where_clause), params, as_dict=True)

	for job in jobs:
		# Calculate total charges
		total_charges = flt(job.get("total_handling_charges", 0)) + flt(job.get("total_storage_charges", 0))
		
		# Calculate unbilled amount
		unbilled_amount = total_charges - flt(job.get("invoiced_amount", 0))
		
		# Get receipt and dispatch counts
		receipt_count = frappe.db.count("Customer Goods Receipt", {"warehouse_job": job.name, "docstatus": 1})
		dispatch_count = frappe.db.count("Customer Goods Dispatch", {"warehouse_job": job.name, "docstatus": 1})

		data.append({
			"name": job.name,
			"job_date": format_date(job.get("job_date")),
			"customer": job.get("customer", ""),
			"reference_number": job.get("reference_number", ""),
			"job_type": job.get("job_type", ""),
			"contract_type": job.get("contract_type", ""),
			"fiscal_year": job.get("fiscal_year", ""),
			"job_start_date": format_date(job.get("job_start_date")),
			"job_end_date": format_date(job.get("job_end_date")),
			"receipt_count": receipt_count,
			"dispatch_count": dispatch_count,
			"total_handling_charges": job.get("total_handling_charges", 0),
			"total_storage_charges": job.get("total_storage_charges", 0),
			"total_charges": total_charges,
			"invoiced_amount": job.get("invoiced_amount", 0),
			"unbilled_amount": unbilled_amount,
			"status": job.get("status", ""),
		})

	return columns, data


def get_columns():
	return [
		{"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Warehouse Job", "width": 150},
		{"label": "Job Date", "fieldname": "job_date", "fieldtype": "Data", "width": 100},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": "Reference", "fieldname": "reference_number", "fieldtype": "Data", "width": 130},
		{"label": "Job Type", "fieldname": "job_type", "fieldtype": "Data", "width": 130},
		{"label": "Contract", "fieldname": "contract_type", "fieldtype": "Data", "width": 110},
		{"label": "Fiscal Year", "fieldname": "fiscal_year", "fieldtype": "Link", "options": "Fiscal Year", "width": 100},
		{"label": "Start Date", "fieldname": "job_start_date", "fieldtype": "Data", "width": 100},
		{"label": "End Date", "fieldname": "job_end_date", "fieldtype": "Data", "width": 100},
		{"label": "Receipts", "fieldname": "receipt_count", "fieldtype": "Int", "width": 80},
		{"label": "Dispatches", "fieldname": "dispatch_count", "fieldtype": "Int", "width": 90},
		{"label": "Handling", "fieldname": "total_handling_charges", "fieldtype": "Currency", "width": 110},
		{"label": "Storage", "fieldname": "total_storage_charges", "fieldtype": "Currency", "width": 110},
		{"label": "Total Charges", "fieldname": "total_charges", "fieldtype": "Currency", "width": 120},
		{"label": "Invoiced", "fieldname": "invoiced_amount", "fieldtype": "Currency", "width": 110},
		{"label": "Unbilled", "fieldname": "unbilled_amount", "fieldtype": "Currency", "width": 110},
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
