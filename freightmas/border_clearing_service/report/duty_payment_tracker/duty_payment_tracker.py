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
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 80},
        {"label": "Border Post", "fieldname": "border_post", "fieldtype": "Link", "options": "Border Post", "width": 120},
        {"label": "Entry Type", "fieldname": "entry_type", "fieldtype": "Data", "width": 120},
        {"label": "Bill of Entry", "fieldname": "bill_of_entry_number", "fieldtype": "Data", "width": 120},
        {"label": "Duty Currency", "fieldname": "assessed_duty_currency", "fieldtype": "Data", "width": 90},
        {"label": "Assessed Duty", "fieldname": "assessed_duty_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Duty Assessed", "fieldname": "is_duty_assessed", "fieldtype": "Check", "width": 100},
        {"label": "Duty Paid", "fieldname": "is_duty_paid", "fieldtype": "Check", "width": 80},
        {"label": "ZIMRA Receipt", "fieldname": "zimra_receipt_number", "fieldtype": "Data", "width": 120},
        {"label": "Pass-Through Total", "fieldname": "total_working_duty_pass_through", "fieldtype": "Currency", "width": 130},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90},
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
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        values["customer"] = filters["customer"]
    if filters.get("border_post"):
        conditions.append("border_post = %(border_post)s")
        values["border_post"] = filters["border_post"]
    if filters.get("company"):
        conditions.append("company = %(company)s")
        values["company"] = filters["company"]
    if filters.get("duty_status") == "Assessed - Not Paid":
        conditions.append("is_duty_assessed = 1")
        conditions.append("is_duty_paid = 0")
    elif filters.get("duty_status") == "Paid":
        conditions.append("is_duty_paid = 1")
    elif filters.get("duty_status") == "Not Assessed":
        conditions.append("is_duty_assessed = 0")

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    fields = [
        "name", "date_created", "customer", "direction", "border_post",
        "entry_type", "bill_of_entry_number",
        "assessed_duty_currency", "assessed_duty_amount",
        "is_duty_assessed", "is_duty_paid", "zimra_receipt_number",
        "total_working_duty_pass_through",
        "status", "company"
    ]

    query = "SELECT {fields} FROM `tabBorder Clearing Job`{where} ORDER BY date_created DESC".format(
        fields=", ".join(fields),
        where=where_clause
    )

    return frappe.db.sql(query, values, as_dict=1)
