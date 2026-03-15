# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_columns(filters):
    charge_type = filters.get("charge_type", "Revenue")

    cols = [
        {"label": "Job No.", "fieldname": "job_name", "fieldtype": "Link", "options": "Border Clearing Job", "width": 140},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Date", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 80},
        {"label": "Border Post", "fieldname": "border_post", "fieldtype": "Link", "options": "Border Post", "width": 120},
        {"label": "Charge", "fieldname": "charge", "fieldtype": "Data", "width": 140},
        {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 160},
        {"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 60},
        {"label": "Pass-Through", "fieldname": "is_pass_through", "fieldtype": "Check", "width": 90},
    ]

    if charge_type == "Revenue":
        cols += [
            {"label": "Rate", "fieldname": "sell_rate", "fieldtype": "Currency", "width": 100},
            {"label": "Amount", "fieldname": "revenue_amount", "fieldtype": "Currency", "width": 120},
            {"label": "Party", "fieldname": "customer_name", "fieldtype": "Link", "options": "Customer", "width": 140},
        ]
    else:
        cols += [
            {"label": "Rate", "fieldname": "buy_rate", "fieldtype": "Currency", "width": 100},
            {"label": "Amount", "fieldname": "cost_amount", "fieldtype": "Currency", "width": 120},
            {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
        ]

    cols.append({"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90})
    return cols


def get_data(filters):
    charge_type = filters.get("charge_type", "Revenue")
    conditions = []
    values = {}

    if filters.get("customer"):
        conditions.append("j.customer = %(customer)s")
        values["customer"] = filters["customer"]
    if filters.get("border_post"):
        conditions.append("j.border_post = %(border_post)s")
        values["border_post"] = filters["border_post"]
    if filters.get("company"):
        conditions.append("j.company = %(company)s")
        values["company"] = filters["company"]
    if filters.get("date_from"):
        conditions.append("j.date_created >= %(date_from)s")
        values["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("j.date_created <= %(date_to)s")
        values["date_to"] = filters["date_to"]

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = " AND " + where_clause

    if charge_type == "Revenue":
        query = """
            SELECT
                c.parent as job_name, j.date_created, j.customer, j.direction,
                j.border_post, c.charge, c.description, c.qty, c.is_pass_through,
                c.sell_rate, c.revenue_amount, c.customer as customer_name,
                j.status
            FROM `tabBorder Clearing Revenue Charges` c
            INNER JOIN `tabBorder Clearing Job` j ON j.name = c.parent
            WHERE c.is_invoiced = 0 {where}
            ORDER BY j.date_created DESC
        """.format(where=where_clause)
    else:
        query = """
            SELECT
                c.parent as job_name, j.date_created, j.customer, j.direction,
                j.border_post, c.charge, c.description, c.qty, c.is_pass_through,
                c.buy_rate, c.cost_amount, c.supplier,
                j.status
            FROM `tabBorder Clearing Cost Charges` c
            INNER JOIN `tabBorder Clearing Job` j ON j.name = c.parent
            WHERE c.is_purchased = 0 {where}
            ORDER BY j.date_created DESC
        """.format(where=where_clause)

    return frappe.db.sql(query, values, as_dict=1)
