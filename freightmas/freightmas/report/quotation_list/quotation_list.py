# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
    
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build conditions and parameters for parameterized query
    conditions = []
    params = {}
    
    if filters.get("from_date"):
        conditions.append("transaction_date >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    
    if filters.get("to_date"):
        conditions.append("transaction_date <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    
    if filters.get("customer"):
        conditions.append("party_name = %(customer)s")
        params["customer"] = filters["customer"]
    
    if filters.get("status"):
        conditions.append("status = %(status)s")
        params["status"] = filters["status"]
    
    if filters.get("job_type"):
        conditions.append("job_type = %(job_type)s")
        params["job_type"] = filters["job_type"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Handle pagination
    limit_clause = ""
    if filters.get("page_length") and filters.get("page_length") != "All":
        page_length = int(filters.get("page_length", 20))
        start = int(filters.get("start", 0))
        limit_clause = f" LIMIT {page_length} OFFSET {start}"

    # Get quotation data
    quotations = frappe.db.sql("""
        SELECT name, transaction_date, party_name as customer, customer_reference,
               valid_till, job_type, grand_total, status
        FROM `tabQuotation`
        WHERE {where_clause}
        ORDER BY transaction_date DESC
        {limit_clause}
    """.format(where_clause=where_clause, limit_clause=limit_clause), params, as_dict=True)

    for quote in quotations:
        data.append({
            "id": quote.name,
            "transaction_date": format_date(quote.get("transaction_date")),
            "customer": quote.get("customer", ""),
            "customer_reference": quote.get("customer_reference", ""),
            "valid_till": format_date(quote.get("valid_till")),
            "job_type": quote.get("job_type", ""),
            "grand_total": quote.get("grand_total", 0),
            "status": quote.get("status", ""),
        })

    # Return data for pagination
    result = {"data": data, "columns": columns}
    
    # Add total count for pagination if limit is applied
    if limit_clause:
        total_count = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabQuotation`
            WHERE {where_clause}
        """.format(where_clause=where_clause), params, as_dict=True)[0].count
        result["total"] = total_count
    
    return columns, data


def get_columns():
    """Get column definitions for the quotation list."""
    return [
        {"label": "Quotation No", "fieldname": "id", "fieldtype": "Link", "options": "Quotation", "width": 190},
        {"label": "Created", "fieldname": "transaction_date", "fieldtype": "Data", "width": 110},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 250},
        {"label": "Customer Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 170},
        {"label": "Valid Till", "fieldname": "valid_till", "fieldtype": "Data", "width": 110},
        {"label": "Job Type", "fieldname": "job_type", "fieldtype": "Data", "width": 120},
        {"label": "Total Amount", "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 130},
    ]


def format_date(date_str):
    """Format date consistently."""
    if not date_str:
        return ""
    return formatdate(date_str, "dd-MMM-yy")
