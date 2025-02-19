# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe.utils import today, get_first_day, get_last_day

def execute(filters=None):
    if not filters:
        filters = {}

    # Set default filters for the current month
    filters.setdefault("start_date", get_first_day(today()))
    filters.setdefault("end_date", get_last_day(today()))

    # SQL Query to fetch Fuel Orders along with Received Litres from Purchase Receipt
    query = """
        SELECT 
            fo.name AS "Fuel Order ID:Link/Fuel Order",
            fo.order_date AS "Order Date:Date",
            fo.truck AS "Truck:Link/Truck",
            fo.supplier AS "Supplier:Link/Supplier",
            fo.required_litres AS "Required Litres:Float",
            fo.actual_litres AS "Actual Litres:Float",
            fo.status AS "Status:Data",
            pr.name AS "Purchase Receipt:Link/Purchase Receipt",
            COALESCE(SUM(pri.qty), 0) AS "Received Litres:Float"
        FROM `tabFuel Order` fo
        LEFT JOIN `tabPurchase Receipt` pr ON pr.reference = fo.name
        LEFT JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE fo.order_date BETWEEN %(start_date)s AND %(end_date)s
    """

    # Apply additional filters if provided
    if filters.get("status"):
        query += " AND fo.status = %(status)s"

    if filters.get("supplier"):
        query += " AND fo.supplier = %(supplier)s"

    # Ensure GROUP BY is applied correctly
    query += """
        GROUP BY fo.name, pr.name
        ORDER BY fo.order_date DESC
    """

    # Fetch data from the database
    data = frappe.db.sql(query, filters, as_list=True)

    # Define Report Columns (Automatically sized by Frappe)
    columns = [
        {"label": "Fuel Order ID", "fieldname": "Fuel Order ID", "fieldtype": "Link", "options": "Fuel Order"},
        {"label": "Order Date", "fieldname": "Order Date", "fieldtype": "Date"},
        {"label": "Truck", "fieldname": "Truck", "fieldtype": "Link", "options": "Truck"},
        {"label": "Supplier", "fieldname": "Supplier", "fieldtype": "Link", "options": "Supplier"},
        {"label": "Required Litres", "fieldname": "Required Litres", "fieldtype": "Float"},
        {"label": "Actual Litres", "fieldname": "Actual Litres", "fieldtype": "Float"},
        {"label": "Status", "fieldname": "Status", "fieldtype": "Data"},
        {"label": "Purchase Receipt", "fieldname": "Purchase Receipt", "fieldtype": "Link", "options": "Purchase Receipt"},
        {"label": "Received Litres", "fieldname": "Received Litres", "fieldtype": "Float"}
    ]

    return columns, data

