# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import flt, today, cstr


class Trip(Document):
    def validate(self):
        """Prevent modification of invoiced revenue charges"""
        for charge in self.trip_revenue_charges:
            if charge.is_invoiced and frappe.flags.in_update:
                frappe.throw(f"You cannot modify an invoiced charge: {charge.charge}")


#######################################################################################
## SALES INVOICE CREATION FROM TRIP REVENUE CHARGES

@frappe.whitelist()
def create_sales_invoice(trip_name, selected_charges, receivable_party):
    """Create a draft Sales Invoice for selected charges."""
    try:
        selected_charges = frappe.parse_json(selected_charges) if isinstance(selected_charges, str) else selected_charges
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

        return {"success": True, "invoice_name": sales_invoice.name}
    
    except Exception as e:
        frappe.log_error(f"Sales Invoice Creation Error: {str(e)}")
        return {"success": False, "error": str(e)}


##################################################################################
## PURCHASE INVOICE CREATION FROM TRIP COST CHARGES

@frappe.whitelist()
def create_purchase_invoice(trip_name, selected_charges, supplier):
    """Create a draft Purchase Invoice for selected cost charges."""
    try:
        selected_charges = frappe.parse_json(selected_charges) if isinstance(selected_charges, str) else selected_charges
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
            "is_trip_invoice": 1,
            "trip_reference": trip_name,
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

        return {"success": True, "invoice_name": purchase_invoice.name}
    
    except Exception as e:
        frappe.log_error(f"Purchase Invoice Creation Error: {str(e)}")
        return {"success": False, "error": str(e)}


#####################################################################################
#### STOCK ENTRY CREATION FROM TRIP FUEL CHARGES

@frappe.whitelist()
def create_fuel_stock_entry_with_rows(docname, row_names):
    try:
        row_names = json.loads(row_names) if isinstance(row_names, str) else row_names
        trip = frappe.get_doc("Trip", docname)

        ste = frappe.new_doc("Stock Entry")
        ste.stock_entry_type = "Material Issue"
        ste.company = trip.company or frappe.defaults.get_user_default("company")
        ste.set_posting_time = 1
        ste.posting_date = today()
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

        if not ste.items:
            frappe.throw("No valid fuel allocation rows found for stock entry creation.")

        ste.insert(ignore_permissions=True)
        stock_entry_name = ste.name

        for row in trip.trip_fuel_allocation:
            if row.name in updated_rows:
                row.stock_entry_reference = stock_entry_name
                row.is_invoiced = 1

        trip.save(ignore_permissions=True)
        return stock_entry_name
    
    except Exception as e:
        frappe.log_error(f"Stock Entry Creation Error: {str(e)}")
        frappe.throw(f"Failed to create Stock Entry: {str(e)}")


################################################################################
### Create Journal Entries from Trip Other Costs - SUBMISSION READY

@frappe.whitelist()
def create_journal_entry_from_other_costs(trip_name, selected_charges):
    """Create a draft Journal Entry for selected other cost charges."""
    try:
        selected_charges = frappe.parse_json(selected_charges) if isinstance(selected_charges, str) else selected_charges
        trip = frappe.get_doc("Trip", trip_name)

        # Create journal entry with proper structure
        je_dict = {
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": frappe.utils.today(),
            "company": trip.company,
            "user_remark": f"Trip Expenses for {trip.name}",
            "accounts": []
        }

        # Process selected charges and build accounts
        for charge_id in selected_charges:
            charge = next((c for c in trip.trip_other_costs if c.name == charge_id), None)
            if not charge:
                continue

            amount = flt(charge.total_amount)
            if amount <= 0:
                continue

            # Create description
            description = charge.item_code or "Trip Expense"
            if charge.description:
                description += f" - {charge.description}"
            
            # Truncate if too long
            if len(description) > 140:
                description = description[:137] + "..."

            # Add debit entry (Expense Account)
            je_dict["accounts"].append({
                "account": charge.expense_account,
                "debit_in_account_currency": amount,
                "cost_center": charge.cost_centre if charge.cost_centre else None,
                "user_remark": description
            })

            # Add credit entry (Contra Account)
            je_dict["accounts"].append({
                "account": charge.contra_account,
                "credit_in_account_currency": amount,
                "cost_center": charge.cost_centre if charge.cost_centre else None,
                "user_remark": description
            })

        if not je_dict["accounts"]:
            frappe.throw("No valid accounting entries found")

        # Create journal entry
        journal_entry = frappe.get_doc(je_dict)
        
        # Add trip reference if field exists (check first)
        if hasattr(journal_entry, 'trip_reference'):
            journal_entry.trip_reference = trip.name

        # Insert without calling validation that might trigger client scripts
        journal_entry.flags.ignore_validate_update_after_submit = True
        journal_entry.flags.ignore_links = True
        journal_entry.insert(ignore_permissions=True)

        # Update trip other costs with journal entry reference
        for charge_id in selected_charges:
            frappe.db.set_value("Trip Other Costs", charge_id, {
                "is_invoiced": 1,
                "journal_entry": journal_entry.name
            })

        # Commit the transaction
        frappe.db.commit()

        return journal_entry.name

    except Exception as e:
        frappe.log_error(f"Journal Entry Creation Error: {str(e)}")
        frappe.throw(f"Failed to create Journal Entry: {str(e)}")


########################################################################
@frappe.whitelist()
def create_additional_salary_from_trip_commissions(docname, row_names):
    try:
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

            if flt(row.amount) <= 0:
                continue

            # Safely handle remarks with proper length limit
            remarks = cstr(row.description or "").strip()
            if len(remarks) > 100:
                remarks = remarks[:97] + "..."

            additional_salary = frappe.get_doc({
                "doctype": "Additional Salary",
                "employee": row.employee,
                "salary_component": row.salary_component,
                "amount": row.amount,
                "payroll_date": trip.end_date or today(),
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

        trip.save(ignore_permissions=True)
        return posted_rows
    
    except Exception as e:
        frappe.log_error(f"Additional Salary Creation Error: {str(e)}")
        frappe.throw(f"Failed to create Additional Salary: {str(e)}")


#####################################################
# Child Table Document Classes

class TripRevenueCharges(Document):
    def validate(self):
        if self.is_invoiced:
            frappe.throw(f"Cannot edit charge '{self.charge}' because it has already been invoiced.")

    def before_delete(self):
        if self.is_invoiced or self.sales_invoice:
            frappe.throw(f"Cannot delete charge '{self.charge}' because it has been invoiced. Associated Invoice: {self.sales_invoice or 'N/A'}.")


class TripCostCharges(Document):
    def validate(self):
        if self.is_invoiced:
            frappe.throw(f"Cannot edit cost charge '{self.charge}' because it has already been invoiced.")

    def before_delete(self):
        if self.is_invoiced or self.purchase_invoice:
            frappe.throw(f"Cannot delete cost charge '{self.charge}' because it has been invoiced. Associated Invoice: {self.purchase_invoice or 'N/A'}.")

