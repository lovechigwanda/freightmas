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

import json
import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_fuel_stock_entry_with_rows(docname, row_names):
    row_names = json.loads(row_names) if isinstance(row_names, str) else row_names
    trip = frappe.get_doc("Trip", docname)

    ste = frappe.new_doc("Stock Entry")
    ste.stock_entry_type = "Material Issue"
    ste.company = frappe.defaults.get_user_default("company")
    ste.set_posting_time = 1
    ste.posting_date = frappe.utils.today()
    ste.trip_reference = trip.name  

    updated_rows = []

    for row in trip.trip_fuel_allocation:
        if row.name not in row_names:
            continue
        if not (row.item and row.qty and row.s_warehouse):
            continue

        ste.append("items", {
            "item_code": row.item,
            "qty": row.qty,
            "s_warehouse": row.s_warehouse,
            "basic_rate": row.rate or 0,
            "cost_center": row.cost_centre,
        })

        updated_rows.append(row.name)

    ste.insert(ignore_permissions=True)
    stock_entry_name = ste.name

    for row in trip.trip_fuel_allocation:
        if row.name in updated_rows:
            row.stock_entry_reference = stock_entry_name
            row.is_invoiced = 1

    trip.save(ignore_permissions=True)
    return stock_entry_name


################################################################################
### Create Journal Entries from Trip Other Costs

@frappe.whitelist()
def create_journal_entry_from_other_costs(docname, row_names):
    import json
    row_names = json.loads(row_names) if isinstance(row_names, str) else row_names
    trip = frappe.get_doc("Trip", docname)

    journal_entry = frappe.new_doc("Journal Entry")
    journal_entry.voucher_type = "Journal Entry"
    journal_entry.posting_date = frappe.utils.today()
    journal_entry.company = frappe.defaults.get_user_default("company")
    journal_entry.trip_reference = trip.name  #Custom field on Journal Entry
    journal_entry.remark = f"Trip Expenses for {trip.name}"

    updated_rows = []

    for row in trip.trip_other_costs:
        if row.name not in row_names:
            continue

        if not (row.item_code and row.quantity and row.rate and row.driver_advance_account and row.expense_account):
            continue

        amount = frappe.utils.flt(row.quantity) * frappe.utils.flt(row.rate)
        if amount <= 0:
            continue

        # Safely sanitize and limit the remark
        safe_remark = (row.description or "").strip()
        if len(safe_remark) > 500:
            safe_remark = safe_remark[:500] + "..."

        journal_entry.append("accounts", {
            "account": row.expense_account,
            "debit_in_account_currency": amount,
            "cost_center": row.cost_centre,
            "user_remark": safe_remark
        })

        journal_entry.append("accounts", {
            "account": row.driver_advance_account,
            "credit_in_account_currency": amount,
            "cost_center": row.cost_centre,
            "user_remark": safe_remark
        })

        updated_rows.append(row.name)

    journal_entry.insert(ignore_permissions=True)
    journal_entry_name = journal_entry.name

    for row in trip.trip_other_costs:
        if row.name in updated_rows:
            row.journal_entry = journal_entry_name
            row.is_invoiced = 1

    trip.save()
    return journal_entry_name

       
########################################################################

@frappe.whitelist()
def create_additional_salary_from_trip_commissions(docname, row_names):
    import json
    row_names = json.loads(row_names) if isinstance(row_names, str) else row_names
    trip = frappe.get_doc("Trip", docname)

    if not trip.company:
        frappe.throw("Please set the Company on the Trip before posting to payroll.")

    posted_rows = []

    for row in trip.trip_commissions:
        if row.name not in row_names:
            continue

        if not (row.employee and row.salary_component and row.amount):
            continue

        if frappe.utils.flt(row.amount) <= 0:
            continue

        remarks = (row.description or "").strip()
        if len(remarks) > 140:
            remarks = remarks[:140] + "..."

        additional_salary = frappe.get_doc({
            "doctype": "Additional Salary",
            "employee": row.employee,
            "salary_component": row.salary_component,
            "amount": row.amount,
            "payroll_date": trip.end_date or frappe.utils.today(),
            "company": trip.company,
            "remarks": f"Trip Bonus for {trip.name}: {remarks}",
            "reference_doctype": "Trip",
            "reference_name": trip.name
        })

        additional_salary.insert(ignore_permissions=True)
        additional_salary.submit()

        row.is_posted_to_payroll = 1
        row.payroll_entry = additional_salary.name
        posted_rows.append(row.name)

    trip.save()
    return posted_rows


#####################################################

