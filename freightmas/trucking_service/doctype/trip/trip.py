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


#### Calculates and returns the Cost Sheet data for a given Trip

import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_trip_cost_sheet(trip_name):
    """
    Fetch and summarize cost sheet details for the given trip.
    """
    trip = frappe.get_doc("Trip", trip_name)

    cost_sheet = []

    # Revenue Charges (Receivable Party)
    receivable_summary = summarize_charges(trip.trip_revenue_charges, "receivable_party", "Sales Invoice")
    for party, summary in receivable_summary.items():
        cost_sheet.append({
            "party": party,
            "charge_type": "Revenue",
            "total_estimated": summary["total_estimated"],
            "total_invoiced": summary["total_invoiced"],
            "difference": summary["total_invoiced"] - summary["total_estimated"],
        })

    # Cost Charges (Payable Party)
    payable_summary = summarize_charges(trip.trip_cost_charges, "payable_party", "Purchase Invoice")
    for party, summary in payable_summary.items():
        cost_sheet.append({
            "party": party,
            "charge_type": "Cost",
            "total_estimated": summary["total_estimated"],
            "total_invoiced": summary["total_invoiced"],
            "difference": summary["total_invoiced"] - summary["total_estimated"],
        })

    return cost_sheet


def summarize_charges(charges, party_field, invoice_field):
    """
    Summarize charges by party and calculate total estimated and invoiced amounts.
    """
    summary = {}
    for charge in charges:
        party = getattr(charge, party_field, None)
        if not party:
            continue

        if party not in summary:
            summary[party] = {"total_estimated": 0, "total_invoiced": 0}

        # Add estimated charge: Use `total_amount` if available, else calculate `rate * quantity`
        estimated_amount = (
            flt(getattr(charge, "total_amount", 0)) or
            flt(getattr(charge, "rate", 0)) * flt(getattr(charge, "quantity", 1))
        )
        summary[party]["total_estimated"] += estimated_amount

        # Add invoiced amount if available
        invoice_name = getattr(charge, invoice_field, None)
        if invoice_name:
            invoice_total = frappe.db.get_value(
                "Sales Invoice" if invoice_field == "Sales Invoice" else "Purchase Invoice",
                invoice_name,
                "total"
            ) or 0
            summary[party]["total_invoiced"] += flt(invoice_total)

    return summary


    ################################################################################