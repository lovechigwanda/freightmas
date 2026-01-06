# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import flt, today, cstr


class Trip(Document):
    def validate(self):
        """Prevent modification of invoiced revenue charges and validate milestones"""
        for charge in self.trip_revenue_charges:
            if charge.is_invoiced and frappe.flags.in_update:
                frappe.throw(f"You cannot modify an invoiced charge: {charge.charge}")
        
        # Validate milestone tracking
        self.validate_milestone_sequence()
        self.validate_milestone_dates()
        self.validate_milestone_requirements()

    def validate_milestone_sequence(self):
        """Ensure milestones are in proper sequence"""
        from frappe import _
        
        milestones = [
            ('is_booked', 'Booked'),
            ('is_loaded', 'Loaded'),
            ('is_offloaded', 'Offloaded'),
            ('is_completed', 'Completed')
        ]
        
        previous_milestone = None
        for milestone_field, milestone_label in milestones:
            current_state = getattr(self, milestone_field, 0)
            
            if current_state and previous_milestone and not getattr(self, previous_milestone[0], 0):
                frappe.throw(
                    _("{0} milestone cannot be completed before {1} milestone")
                    .format(milestone_label, previous_milestone[1])
                )
            
            if current_state:
                previous_milestone = (milestone_field, milestone_label)
        
        # Validate is_returned separately (optional milestone for containerised cargo)
        if getattr(self, 'is_returned', 0):
            if self.cargo_type != 'Containerised':
                frappe.throw(
                    _("Container return milestone can only be set for Containerised cargo")
                )
            if not getattr(self, 'is_offloaded', 0):
                frappe.throw(
                    _("Trip must be offloaded before marking as returned")
                )

    def validate_milestone_dates(self):
        """Ensure milestone dates are in chronological order and not in future"""
        from frappe import _
        from frappe.utils import getdate, nowdate
        
        date_fields = [
            ('booked_on_date', 'Booked Date'),
            ('loaded_on_date', 'Loaded Date'),
            ('offloaded_on_date', 'Offloaded Date'),
            ('returned_on_date', 'Returned Date'),
            ('completed_on_date', 'Completed Date')
        ]
        
        dates_with_values = []
        today = getdate(nowdate())
        
        for field, label in date_fields:
            date_value = getattr(self, field, None)
            if date_value:
                try:
                    normalized_date = getdate(date_value)
                    
                    # Check for future dates
                    if normalized_date > today:
                        frappe.throw(
                            _("{0} cannot be in the future")
                            .format(label)
                        )
                    
                    dates_with_values.append((field, label, normalized_date))
                    
                except Exception:
                    frappe.throw(
                        _("Invalid date format in {0}")
                        .format(label)
                    )
        
        # Check chronological order
        for i in range(1, len(dates_with_values)):
            if dates_with_values[i][2] < dates_with_values[i-1][2]:
                frappe.throw(
                    _("{0} cannot be before {1}")
                    .format(dates_with_values[i][1], dates_with_values[i-1][1])
                )

    def validate_milestone_requirements(self):
        """Validate required fields for specific milestones"""
        from frappe import _
        
        # Required for loading
        if getattr(self, 'is_loaded', 0):
            if not self.driver:
                frappe.throw(_("Driver is required for loaded trip"))
            if not self.truck:
                frappe.throw(_("Truck is required for loaded trip"))
        
        # Required for completion
        if getattr(self, 'is_completed', 0):
            if not getattr(self, 'is_offloaded', 0):
                frappe.throw(_("Trip must be offloaded before marking as completed"))


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
        
        # Create single line remark from trip details
        remark = f"{trip.name}"
        if trip.truck:
            remark += f" {trip.truck}"
        if trip.route:
            remark += f" {trip.route}"
        if trip.cargo_description:
            remark += f" {trip.cargo_description}"

        # Prepare invoice items from selected charges
        items = []
        for charge_id in selected_charges:
            charge = next((c for c in trip.trip_revenue_charges if c.name == charge_id), None)
            if not charge:
                frappe.throw(f"Charge with ID {charge_id} not found.")
            if charge.is_invoiced:
                frappe.throw(f"Charge '{charge.charge}' has already been invoiced. Please refresh and try again.")

            items.append({
                "item_code": charge.charge,
                "description": charge.charge_description,
                "qty": charge.quantity or 1,
                "rate": flt(charge.rate),
                "amount": charge.total_amount or 0,
                "cost_center": charge.cost_centre  # Add this line
            })

        # Create a Sales Invoice
        sales_invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": receivable_party,
            "is_trip_invoice": 1,
            "trip_reference": trip_name,
            "items": items,
            "remarks": remark
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
################################################
# Bulk Invoice Creation
@frappe.whitelist()
def create_bulk_invoices(selected_charges, group_invoice=0):
    import json
    if isinstance(selected_charges, str):
        selected_charges = json.loads(selected_charges)
    group_invoice = int(group_invoice)

    # Group charges by (trip, receivable_party)
    trip_charge_map = {}
    charge_invoice_map = {}
    created_invoices = []

    for entry in selected_charges:
        trip_name = entry['trip']
        charge_id = entry['charge']
        trip = frappe.get_doc("Trip", trip_name)
        charge = next((c for c in trip.trip_revenue_charges if c.name == charge_id), None)
        if not charge:
            continue
        receivable_party = charge.receivable_party
        key = (trip_name, receivable_party)
        trip_charge_map.setdefault(key, []).append(charge_id)

    # Create individual invoices per (trip, receivable_party)
    for (trip_name, receivable_party), charge_ids in trip_charge_map.items():
        invoice_result = create_sales_invoice(
            trip_name=trip_name,
            selected_charges=charge_ids,
            receivable_party=receivable_party
        )
        if invoice_result.get("success"):
            invoice = frappe.get_doc("Sales Invoice", invoice_result["invoice_name"])
            invoice.submit()
            created_invoices.append(invoice.name)
            # Map each charge to its invoice for bulk invoice item rows
            for charge_id in charge_ids:
                charge_invoice_map[(trip_name, charge_id)] = invoice.name

    # If group_invoice, create a Trip Bulk Sales Invoice with per-charge details
    bulk_invoice = None
    if group_invoice and created_invoices:
        # Use the first trip and receivable_party for header info
        first_key = next(iter(trip_charge_map))
        sample_trip = frappe.get_doc("Trip", first_key[0])
        customer = first_key[1]

        # Build per-charge item rows
        bulk_items = []
        for entry in selected_charges:
            trip_name = entry['trip']
            charge_id = entry['charge']
            trip = frappe.get_doc("Trip", trip_name)
            charge = next((c for c in trip.trip_revenue_charges if c.name == charge_id), None)
            if not charge:
                continue
            bulk_items.append({
                "trip": trip_name,
                "truck": charge.truck,  # <-- Fetch truck from the charge row
                "sales_invoice": charge_invoice_map.get((trip_name, charge_id)),
                "charge": charge.charge,
                "description": charge.charge_description,
                "qty": charge.quantity,
                "rate": charge.rate,
                "amount": charge.total_amount
            })

        bulk_invoice = frappe.get_doc({
            "doctype": "Trip Bulk Sales Invoice",
            "customer": customer,
            "date_created": frappe.utils.today(),
            "trip_direction": sample_trip.trip_direction,
            "route": sample_trip.route,
            "cargo_type": sample_trip.cargo_type,
            "trip_bulk_sales_invoice_item": bulk_items
        })
        bulk_invoice.insert()

    return {
        "invoices": created_invoices,
        "bulk_invoice": bulk_invoice.name if bulk_invoice else None
    }

@frappe.whitelist()
def get_uninvoiced_trips(filters):
    filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
    trip_conditions = []
    values = {}

    for field in ["route", "trip_direction", "cargo_type"]:
        if filters.get(field):
            trip_conditions.append(f"{field} = %({field})s")
            values[field] = filters[field]
    if filters.get("from_date"):
        trip_conditions.append("date_created >= %(from_date)s")
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        trip_conditions.append("date_created <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    trip_query = f"""
        SELECT name, customer, route, trip_direction, cargo_type, date_created
        FROM `tabTrip`
        WHERE 1=1
        {'AND ' + ' AND '.join(trip_conditions) if trip_conditions else ''}
    """
    trips = frappe.db.sql(trip_query, values, as_dict=True)

    customer = filters.get("customer")
    result = []
    for trip in trips:
        charges = frappe.db.get_all(
            "Trip Revenue Charges",
            filters={
                "parent": trip["name"],
                "is_invoiced": 0,
                "receivable_party": customer
            },
            fields=[
                "name", "charge", "quantity", "rate", "total_amount", "receivable_party",
                "truck"  # <-- Add this!
            ]
        )
        if charges:
            trip["revenue_charges"] = charges
            result.append(trip)

    return result

