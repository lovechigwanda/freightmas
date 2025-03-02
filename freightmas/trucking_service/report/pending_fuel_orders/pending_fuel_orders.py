# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe.utils import today, get_first_day, get_last_day

def execute(filters=None):
    # Fetch only pending fuel orders
    query = """
        SELECT 
            fo.name AS "Fuel Order ID:Link/Fuel Order",
            fo.order_date AS "Order Date:Date",
            fo.truck AS "Truck:Link/Truck",
            fo.supplier AS "Supplier:Link/Supplier",
            fo.required_litres AS "Required Litres:Float",
            fo.requested_by AS "Requested By:Link/User",
            fo.status AS "Status:Data"
        FROM `tabFuel Order` fo
        WHERE fo.status = 'Pending Approval'
        ORDER BY fo.order_date DESC
    """
    
    # Fetch data from the database
    data = frappe.db.sql(query, as_list=True)

    # Define Report Columns
    columns = [
        {"label": "Fuel Order ID", "fieldname": "Fuel Order ID", "fieldtype": "Link", "options": "Fuel Order"},
        {"label": "Order Date", "fieldname": "Order Date", "fieldtype": "Date"},
        {"label": "Truck", "fieldname": "Truck", "fieldtype": "Link", "options": "Truck"},
        {"label": "Supplier", "fieldname": "Supplier", "fieldtype": "Link", "options": "Supplier"},
        {"label": "Required Litres", "fieldname": "Required Litres", "fieldtype": "Float"},
        {"label": "Requested By", "fieldname": "Requested By", "fieldtype": "Link", "options": "User"},
        {"label": "Status", "fieldname": "Status", "fieldtype": "Data"}
    ]
    
    return columns, data
