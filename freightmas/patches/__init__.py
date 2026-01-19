# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe

def execute():
    """
    Delete old workspace names that have been replaced:
    - Forwarding Service -> Freight Forwarding
    - Trucking Service -> Trucking
    - Road Freight Service -> Road Freight
    """
    old_workspaces = [
        "Forwarding Service",
        "Trucking Service", 
        "Road Freight Service"
    ]
    
    for workspace_name in old_workspaces:
        if frappe.db.exists("Workspace", workspace_name):
            frappe.delete_doc("Workspace", workspace_name, force=True, ignore_permissions=True)
            frappe.db.commit()
            print(f"Deleted old workspace: {workspace_name}")
