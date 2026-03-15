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
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 70},
        {"label": "Revenue", "fieldname": "total_actual_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Cost", "fieldname": "total_actual_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Profit", "fieldname": "total_actual_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Duty (Pass-Through)", "fieldname": "total_working_duty_pass_through", "fieldtype": "Currency", "width": 140},
        {"label": "Margin %", "fieldname": "margin_pct", "fieldtype": "Percent", "width": 80},
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
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        values["customer"] = filters["customer"]
    if filters.get("border_post"):
        conditions.append("border_post = %(border_post)s")
        values["border_post"] = filters["border_post"]
    if filters.get("company"):
        conditions.append("company = %(company)s")
        values["company"] = filters["company"]
    if filters.get("status"):
        conditions.append("status = %(status)s")
        values["status"] = filters["status"]

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    fields = [
        "name", "date_created", "customer", "direction", "border_post",
        "currency", "total_actual_revenue", "total_actual_cost", "total_actual_profit",
        "total_working_duty_pass_through",
        "status", "completed_on", "company"
    ]

    query = "SELECT {fields} FROM `tabBorder Clearing Job`{where} ORDER BY date_created DESC".format(
        fields=", ".join(fields),
        where=where_clause
    )

    data = frappe.db.sql(query, values, as_dict=1)

    for row in data:
        revenue = flt(row.get("total_actual_revenue"))
        if revenue:
            row["margin_pct"] = flt(row.get("total_actual_profit")) / revenue * 100
        else:
            row["margin_pct"] = 0

    return data
