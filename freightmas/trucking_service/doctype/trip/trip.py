# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Trip(Document):
    pass

#######################################################################################

## SALES INVOICE CREATION FROM TRIP REVENUE CHARGES

import frappe
from frappe.utils import flt

@frappe.whitelist()
def create_sales_invoice(trip_name, selected_charges, receivable_party):
    """Create a draft Sales Invoice for selected charges."""
    selected_charges = frappe.parse_json(selected_charges)  # Ensure data is parsed correctly
    if not selected_charges:
        frappe.throw("No charges selected for invoicing.")

    trip = frappe.get_doc("Trip", trip_name)

    # Prepare invoice items from selected charges
    items = []
    for charge_id in selected_charges:
        charge = next((c for c in trip.trip_revenue_charges if c.name == charge_id), None)
        if not charge:
            frappe.throw(f"Charge with ID {charge_id} not found.")
        if charge.is_invoiced:
            frappe.throw(f"Charge '{charge.charge}' has already been invoiced.")

        items.append({
            "item_code": charge.charge,
            "description": charge.charge_description,
            "qty": charge.quantity or 1,
            "rate": flt(charge.rate),
        })

    # Create a Sales Invoice
    sales_invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": receivable_party,
        "is_trip_invoice": 1,
        "trip_reference": trip_name,
        "items": items,
    })

    # Save as draft
    sales_invoice.insert()

    # Update `sales_invoice` field for the selected charges
    for charge_id in selected_charges:
        charge = next((c for c in trip.trip_revenue_charges if c.name == charge_id), None)
        if charge:
            charge.is_invoiced = 1
            charge.sales_invoice = sales_invoice.name
    trip.save()

    return {"invoice_name": sales_invoice.name}



##############################################################################################

##PREVENT MODIFICATION OF INVOICED REVENUE CHARGES

def validate(self):
    for charge in self.trip_revenue_charges:
        if charge.is_invoiced and frappe.flags.in_update:
            frappe.throw(f"You cannot modify an invoiced charge: {charge.charge}")


###################################################################################################

##PREVENT MODIFICATION AND DELETION OF INVOICED REVENUE CHARGES

import frappe
from frappe.model.document import Document

class TripRevenueCharges(Document):
    def validate(self):
        """
        Prevent editing of invoiced charges.
        """
        if self.is_invoiced:
            frappe.throw(f"Cannot edit charge '{self.charge}' because it has already been invoiced.")

    def before_delete(self):
        """
        Prevent deletion of invoiced charges.
        """
        if self.is_invoiced or self.sales_invoice:
            frappe.throw(f"Cannot delete charge '{self.charge}' because it has been invoiced. Associated Invoice: {self.sales_invoice or 'N/A'}.")


##################################################################################

## PURCHASE INVOICE CREATION FROM TRIP COST CHARGES

import frappe
from frappe.utils import flt

@frappe.whitelist()
def create_purchase_invoice(trip_name, selected_charges, supplier):
    """Create a draft Purchase Invoice for selected cost charges."""
    selected_charges = frappe.parse_json(selected_charges)  # Ensure data is parsed correctly
    if not selected_charges:
        frappe.throw("No charges selected for invoicing.")

    trip = frappe.get_doc("Trip", trip_name)

    # Prepare invoice items from selected cost charges
    items = []
    for charge_id in selected_charges:
        charge = next((c for c in trip.trip_cost_charges if c.name == charge_id), None)
        if not charge:
            frappe.throw(f"Charge with ID {charge_id} not found.")
        if charge.is_invoiced:
            frappe.throw(f"Charge '{charge.charge}' has already been invoiced.")

        items.append({
            "item_code": charge.charge,
            "description": charge.charge_description,
            "qty": charge.quantity or 1,
            "rate": flt(charge.rate),
        })

    # Create a Purchase Invoice
    purchase_invoice = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": supplier,
        "is_trip_invoice": 1,  # Custom field to indicate this is a trip-related invoice
        "trip_reference": trip_name,  # Custom field to link the invoice to the trip
        "items": items,
    })

    # Save as draft
    purchase_invoice.insert()

    # Update `purchase_invoice` field for the selected cost charges
    for charge_id in selected_charges:
        charge = next((c for c in trip.trip_cost_charges if c.name == charge_id), None)
        if charge:
            charge.is_invoiced = 1
            charge.purchase_invoice = purchase_invoice.name
    trip.save()

    return {"invoice_name": purchase_invoice.name}

################################################

##PREVENT MODIFICATION AND DELETION OF INVOICED COST CHARGES

import frappe
from frappe.model.document import Document

class TripCostCharges(Document):
    def validate(self):
        """
        Prevent editing of invoiced charges.
        """
        if self.is_invoiced:
            frappe.throw(f"Cannot edit cost charge '{self.charge}' because it has already been invoiced.")

    def before_delete(self):
        """
        Prevent deletion of invoiced charges.
        """
        if self.is_invoiced or self.purchase_invoice:
            frappe.throw(f"Cannot delete cost charge '{self.charge}' because it has been invoiced. Associated Invoice: {self.purchase_invoice or 'N/A'}.")

#####################################################################################


#### STOCK ENTRY CREATION FROM TRIP FUEL CHARGES
import frappe
from frappe.utils import flt

@frappe.whitelist()
def create_stock_entry_from_fuel_costs(trip_name, selected_costs, source_warehouse):
    """Create a Stock Entry for selected fuel costs."""
    import json
    selected_costs = json.loads(selected_costs)  # Parse JSON data
    if not selected_costs:
        frappe.throw("No fuel costs selected for stock entry.")

    trip = frappe.get_doc("Trip", trip_name)

    # Prepare Stock Entry items
    items = []
    for cost_id in selected_costs:
        cost = next((c for c in trip.trip_fuel_costs if c.name == cost_id), None)
        if not cost:
            frappe.throw(f"Cost with ID {cost_id} not found in Trip Fuel Costs.")
        if cost.is_invoiced:
            frappe.throw(f"Fuel cost for item '{cost.item_code}' has already been invoiced or used.")

        items.append({
            "item_code": cost.item_code,
            "qty": flt(cost.quantity),
            "rate": flt(cost.rate),
            "s_warehouse": source_warehouse,
        })

    if not items:
        frappe.throw("No valid items to create the Stock Entry.")

    # Create the Stock Entry
    stock_entry = frappe.get_doc({
        "doctype": "Stock Entry",
        "stock_entry_type": "Material Issue",
        "items": items,
        "company": trip.company,
        "trip_reference": trip_name,
        "remarks": f"Stock issued for Trip {trip_name}",
    })

    # Save the Stock Entry
    stock_entry.insert()

    # Update the fuel costs table
    for cost_id in selected_costs:
        cost = next((c for c in trip.trip_fuel_costs if c.name == cost_id), None)
        if cost:
            cost.is_invoiced = 1
            cost.stock_entry = stock_entry.name
    trip.save()

    return {"stock_entry_name": stock_entry.name}






    ################################################################################

    ##Prevent Editing or Deletion of Used Fuel Charges


def validate(self):
    for fuel_cost in self.trip_fuel_costs:
        if fuel_cost.is_invoiced and frappe.flags.in_update:
            frappe.throw(f"You cannot modify an invoiced fuel cost: {fuel_cost.item_code}")



import frappe
from frappe.model.document import Document

class TripFuelCosts(Document):
    def validate(self):
        """
        Prevent editing of invoiced fuel costs.
        """
        if self.is_invoiced:
            frappe.throw(f"Cannot edit fuel cost for item '{self.item_code}' because it has already been invoiced.")

    def before_delete(self):
        """
        Prevent deletion of invoiced fuel costs.
        """
        if self.is_invoiced or self.stock_entry:
            frappe.throw(f"Cannot delete fuel cost for item '{self.item_code}' because it has been invoiced. Associated Stock Entry: {self.stock_entry or 'N/A'}.")

    
########################################################################



#####################################################

