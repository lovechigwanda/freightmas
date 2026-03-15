# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Job No.", "fieldname": "name", "fieldtype": "Link", "options": "Border Clearing Job", "width": 140},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Date", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Customer Ref", "fieldname": "customer_reference", "fieldtype": "Data", "width": 110},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 80},
        {"label": "Border Post", "fieldname": "border_post", "fieldtype": "Link", "options": "Border Post", "width": 120},
        {"label": "Entry Type", "fieldname": "entry_type", "fieldtype": "Data", "width": 120},
        {"label": "Bill of Entry", "fieldname": "bill_of_entry_number", "fieldtype": "Data", "width": 120},
        {"label": "Clearing Agent", "fieldname": "clearing_agent", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 70},
        {"label": "Conv. Rate", "fieldname": "conversion_rate", "fieldtype": "Float", "width": 80},
        {"label": "Est. Revenue", "fieldname": "total_quoted_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Cost", "fieldname": "total_quoted_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Profit", "fieldname": "total_quoted_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": "Completed On", "fieldname": "completed_on", "fieldtype": "Date", "width": 100},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("date_from"):
        conditions.append("date_created >= %(date_from)s")
        values["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("date_created <= %(date_to)s")
        values["date_to"] = filters["date_to"]
    if filters.get("direction"):
        conditions.append("direction = %(direction)s")
        values["direction"] = filters["direction"]
    if filters.get("status"):
        conditions.append("status = %(status)s")
        values["status"] = filters["status"]
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        values["customer"] = filters["customer"]
    if filters.get("border_post"):
        conditions.append("border_post = %(border_post)s")
        values["border_post"] = filters["border_post"]
    if filters.get("company"):
        conditions.append("company = %(company)s")
        values["company"] = filters["company"]

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    fields = [
        "name", "date_created", "customer", "customer_reference", "direction",
        "border_post", "entry_type", "bill_of_entry_number", "clearing_agent",
        "currency", "conversion_rate",
        "total_quoted_revenue", "total_quoted_cost", "total_quoted_profit",
        "status", "completed_on", "company"
    ]

    query = "SELECT {fields} FROM `tabBorder Clearing Job`{where} ORDER BY date_created DESC".format(
        fields=", ".join(fields),
        where=where_clause
    )

    return frappe.db.sql(query, values, as_dict=1)
