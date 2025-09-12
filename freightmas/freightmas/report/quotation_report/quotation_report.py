# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Quotation"), "fieldname": "name", "fieldtype": "Link", "options": "Quotation", "width": 200},
        {"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 280},
        {"label": _("Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 110},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Revenue"), "fieldname": "est_revenue", "fieldtype": "Currency", "width": 120},
        {"label": _("Cost"), "fieldname": "est_cost", "fieldtype": "Currency", "width": 120},
        {"label": _("Profit"), "fieldname": "profit", "fieldtype": "Currency", "width": 120},
        {"label": _("Profit %"), "fieldname": "profit_percent", "fieldtype": "Percent", "width": 100},
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    quotations = frappe.db.sql(f"""
        SELECT
            q.name,
            q.customer_name,
            q.transaction_date,
            q.status,
            q.est_revenue,
            q.est_cost,
            (q.est_revenue - q.est_cost) as profit,
            CASE WHEN q.est_revenue > 0 THEN ROUND(100 * (q.est_revenue - q.est_cost) / q.est_revenue, 2) ELSE 0 END as profit_percent
        FROM `tabQuotation` q
        WHERE 1=1 {conditions}
        ORDER BY q.transaction_date DESC
    """, as_dict=1)
    return quotations

def get_conditions(filters):
    conditions = ""
    if filters.get("from_date"):
        conditions += f" AND q.transaction_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"):
        conditions += f" AND q.transaction_date <= '{filters.get('to_date')}'"
    if filters.get("customer"):
        conditions += f" AND q.customer_name = '{filters.get('customer')}'"
    if filters.get("status"):
        conditions += f" AND q.status = '{filters.get('status')}'"
    return conditions
