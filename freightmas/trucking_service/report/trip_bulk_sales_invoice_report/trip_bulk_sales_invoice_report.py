# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def format_date(date_str):
    if not date_str:
        return ""
    try:
        return frappe.utils.formatdate(date_str, "dd-MMM-yy")
    except Exception:
        return date_str


def get_columns():
    return [
        {"label": "Invoice No", "fieldname": "name", "fieldtype": "Link", "options": "Trip Bulk Sales Invoice", "width": 160},
        {"label": "Date", "fieldname": "date_created", "fieldtype": "Data", "width": 110},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 270},
        {"label": "Total Qty", "fieldname": "total_quantity", "fieldtype": "Int", "width": 110},
        {"label": "Sub Total", "fieldname": "sub_total", "fieldtype": "Currency", "width": 130},
        {"label": "VAT", "fieldname": "vat", "fieldtype": "Currency", "width": 130},
        {"label": "Grand Total", "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 140},
    ]


def execute(filters=None):
    columns = get_columns()
    data = []

    filters = filters or {}
    invoice_filters = {}

    if filters.get("from_date") and filters.get("to_date"):
        invoice_filters["date_created"] = ["between", [filters["from_date"], filters["to_date"]]]
    if filters.get("customer"):
        invoice_filters["customer"] = filters["customer"]
    if filters.get("status"):
        invoice_filters["status"] = filters["status"]

    invoices = frappe.get_all(
        "Trip Bulk Sales Invoice",
        filters=invoice_filters,
        fields=[
            "name", "date_created", "customer",
            "total_quantity", "sub_total", "vat", "grand_total", "status"
        ]
    )

    for inv in invoices:
        data.append({
            "name": inv.get("name", ""),
            "date_created": format_date(inv["date_created"]),
            "customer": inv.get("customer", ""),
            "total_quantity": inv.get("total_quantity", 0),
            "sub_total": inv.get("sub_total", 0),
            "vat": inv.get("vat", 0),
            "grand_total": inv.get("grand_total", 0),
            "status": inv.get("status", ""),
        })

    return columns, data
