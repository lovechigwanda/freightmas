# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Truck(Document):
    def validate(self):
        self.validate_unique_driver()
        self.validate_unique_trailer()
    
    def validate_unique_driver(self):
        """Ensure that a driver is not assigned to multiple trucks"""
        if self.assigned_driver:
            # Check if this driver is already assigned to another truck
            existing_truck = frappe.db.get_value(
                "Truck", 
                {
                    "assigned_driver": self.assigned_driver,
                    "name": ["!=", self.name]  # Exclude current truck
                }, 
                "name"
            )
            
            if existing_truck:
                frappe.throw(
                    _("Driver {0} is already assigned to Truck {1}. A driver can only be assigned to one truck at a time.").format(
                        frappe.bold(self.assigned_driver), 
                        frappe.bold(existing_truck)
                    )
                )
    
    def validate_unique_trailer(self):
        """Ensure that a trailer is not assigned to multiple trucks"""
        if self.assigned_trailer:
            # Check if this trailer is already assigned to another truck
            existing_truck = frappe.db.get_value(
                "Truck", 
                {
                    "assigned_trailer": self.assigned_trailer,
                    "name": ["!=", self.name]  # Exclude current truck
                }, 
                "name"
            )
            
            if existing_truck:
                frappe.throw(
                    _("Trailer {0} is already assigned to Truck {1}. A trailer can only be assigned to one truck at a time.").format(
                        frappe.bold(self.assigned_trailer), 
                        frappe.bold(existing_truck)
                    )
                )
