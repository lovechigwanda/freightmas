# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Truck(Document):
	pass

import frappe

def after_insert(doc, method):
    # Define the parent warehouse name
    parent_warehouse_name = "Fuel in Trucks"

    # Check and create the parent warehouse if it doesn't exist
    if not frappe.db.exists("Warehouse", parent_warehouse_name):
        # Get the top-level warehouse
        top_level_warehouse = frappe.db.get_value("Warehouse", {}, "name")
        if not top_level_warehouse:
            frappe.throw("No top-level warehouse found. Please create one manually.")
        
        parent_warehouse = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": parent_warehouse_name,
            "parent_warehouse": top_level_warehouse  # Use the detected top-level warehouse
        })
        parent_warehouse.insert()

    # Create a warehouse for the truck
    warehouse_name = f"{doc.name} - Fuel"
    if not frappe.db.exists("Warehouse", warehouse_name):
        warehouse = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": warehouse_name,
            "parent_warehouse": parent_warehouse_name,
        })
        warehouse.insert()
        doc.warehouse = warehouse.name
        doc.save()
