# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class FuelOrder(Document):
	pass


########## Create Purchase Receipt ##################


import frappe

@frappe.whitelist()
def create_purchase_receipt(fuel_order):
    """Creates a draft Purchase Receipt from a Fuel Order with auto-generated remark and reference."""

    doc = frappe.get_doc("Fuel Order", fuel_order)
    
    # Validation: Ensure the order is completed
    if doc.status != "Completed":
        frappe.throw("Purchase Receipt can only be created when the Fuel Order is marked as Completed.")

    # Validation: Ensure actual litres are entered
    if not doc.actual_litres or doc.actual_litres <= 0:
        frappe.throw("Actual Litres must be entered before creating a Purchase Receipt.")

    # Validation: Ensure required fields are present
    required_fields = ["truck", "supplier", "item_code", "warehouse"]
    for field in required_fields:
        if not doc.get(field):
            frappe.throw(f"{field.replace('_', ' ').title()} must be selected before creating a Purchase Receipt.")

    # Prevent duplicate Purchase Receipts
    existing_pr = frappe.db.exists("Purchase Receipt", {"fuel_order": doc.name})
    if existing_pr:
        frappe.throw(f"Purchase Receipt {existing_pr} already exists for this Fuel Order.")

    # Generate Remark
    remark = f"Purchase {doc.item_name} {doc.actual_litres} Litres from {doc.supplier} for {doc.truck} (Fuel Order: {doc.name})."

    # Create the Purchase Receipt using the warehouse from Fuel Order
    purchase_receipt = frappe.get_doc({
        "doctype": "Purchase Receipt",
        "supplier": doc.supplier,
        "posting_date": frappe.utils.today(),
        "set_warehouse": doc.warehouse,  # Using the fetched warehouse from Truck
        "items": [{
            "item_code": doc.item_code,
            "qty": doc.actual_litres,
            "uom": "Litre",
            "stock_uom": "Litre",
            "warehouse": doc.warehouse  # Use the pre-fetched warehouse
        }],
        "fuel_order": doc.name,  # Custom field linking the Fuel Order
        "reference": doc.name,  # Auto-fill Reference field
        "remarks": remark,  # Auto-generated remark (formerly "narration")
        "docstatus": 0  # Keep in Draft mode
    })

    # Save the Purchase Receipt
    purchase_receipt.insert(ignore_permissions=True)

    # Link the created Purchase Receipt to the Fuel Order
    doc.db_set("purchase_receipt", purchase_receipt.name)

    return purchase_receipt.name  # Return the created document name


############################################################################
###Automatically Capture Approval Data 

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class FuelOrder(Document):
    def before_save(self):
        # Ensure order creation time is recorded (if not already set)
        if not self.get("order_creation_time"):
            self.order_creation_time = self.creation

    def before_submit(self):
        # Capture Approval Details (when submitting as "Approved")
        if self.status == "Approved" and not self.get("approval_time"):
            self.approved_by = frappe.session.user
            self.approval_time = now_datetime()


#############################################################