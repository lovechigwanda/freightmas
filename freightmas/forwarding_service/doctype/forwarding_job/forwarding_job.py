# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, cint
from frappe import _

class ForwardingJob(Document):
    
    def validate(self):
        """Validate document before saving"""
        # Set completed_on when status is Completed
        if self.status == "Completed" and not self.completed_on:
            self.completed_on = nowdate()
        
        # Set base currency first
        self.set_base_currency()
        
        # Calculate costing charges
        self.calculate_costing_charges()
        self.calculate_costing_totals()
        
        # Calculate actual charges
        self.calculate_actual_revenue_charges()
        self.calculate_actual_cost_charges()
        self.calculate_actual_totals()
        
        # Validate customer and supplier information
        self.validate_customer_and_supplier()
        
        # Prevent editing of invoiced rows
        self.prevent_editing_invoiced_rows()
        
        # Calculate the number of trucks required
        self.calculate_trucks_required()

        # Ensure planned charges exist before leaving Draft
        self.ensure_planned_charges_before_status_change()
        
        # Prevent editing of costing charges once job is not Draft
        self.prevent_editing_costing_charges()
        
        # Validate cargo milestone progression
        self.validate_cargo_milestones()
        
        # Validate completion requirements before status changes to Completed
        self.validate_completion_requirements()

    def on_submit(self):
        """Handle job submission - trigger revenue and cost recognition"""
        # Validate Revenue Recognition Date before proceeding
        self.validate_revenue_recognition_before_submit()
        
        from freightmas.utils.revenue_recognition import recognize_revenue_for_job, recognize_cost_for_job
        recognize_revenue_for_job(self, "forwarding")
        recognize_cost_for_job(self, "forwarding")

    def on_cancel(self):
        """Handle job cancellation - reverse revenue and cost recognition"""
        from freightmas.utils.revenue_recognition import reverse_revenue_recognition, reverse_cost_recognition
        reverse_revenue_recognition(self)
        reverse_cost_recognition(self)

    def set_base_currency(self):
        """Ensure base_currency and conversion_rate are set."""
        if not getattr(self, "base_currency", None) and getattr(self, "company", None):
            self.base_currency = frappe.db.get_value("Company", self.company, "default_currency")

        if not getattr(self, "conversion_rate", None):
            try:
                from erpnext.setup.utils import get_exchange_rate
                if self.currency and self.base_currency and self.currency != self.base_currency:
                    self.conversion_rate = flt(get_exchange_rate(self.currency, self.base_currency)) or 1.0
                else:
                    self.conversion_rate = 1.0
            except Exception:
                self.conversion_rate = 1.0

    def calculate_costing_charges(self):
        """Compute line amounts for costing table."""
        for charge in self.get("forwarding_costing_charges", []):
            qty = flt(charge.qty) or 1
            sell_rate = flt(charge.sell_rate) or 0
            buy_rate = flt(charge.buy_rate) or 0

            charge.revenue_amount = qty * sell_rate
            charge.cost_amount = qty * buy_rate
            charge.margin_amount = charge.revenue_amount - charge.cost_amount
            charge.margin_percentage = (
                (charge.margin_amount / charge.revenue_amount) * 100 if charge.revenue_amount else 0
            )

    def calculate_costing_totals(self):
        """Totals for costing section."""
        total_revenue = 0
        total_cost = 0

        for charge in self.get("forwarding_costing_charges", []):
            total_revenue += flt(charge.revenue_amount)
            total_cost += flt(charge.cost_amount)

        total_profit = total_revenue - total_cost
        rate = flt(self.conversion_rate) or 1.0

        self.total_quoted_revenue = total_revenue
        self.total_quoted_cost = total_cost
        self.total_quoted_margin = total_profit

        self.total_quoted_revenue_base = total_revenue * rate
        self.total_quoted_cost_base = total_cost * rate
        self.total_quoted_profit_base = total_profit * rate

        self.quoted_margin_percent = (
            (total_profit / total_revenue) * 100 if total_revenue else 0
        )

    def calculate_actual_revenue_charges(self):
        """Compute line amounts for actual revenue table."""
        for charge in self.get("forwarding_revenue_charges", []):
            qty = flt(charge.qty) or 1
            sell_rate = flt(charge.sell_rate) or 0
            charge.revenue_amount = qty * sell_rate

    def calculate_actual_cost_charges(self):
        """Compute line amounts for actual cost table."""
        for charge in self.get("forwarding_cost_charges", []):
            qty = flt(charge.qty) or 1
            buy_rate = flt(charge.buy_rate) or 0
            charge.cost_amount = qty * buy_rate

    def calculate_actual_totals(self):
        """Totals for actual section."""
        total_revenue = 0
        for charge in self.get("forwarding_revenue_charges", []):
            total_revenue += flt(charge.revenue_amount)

        total_cost = 0
        for charge in self.get("forwarding_cost_charges", []):
            total_cost += flt(charge.cost_amount)

        total_profit = total_revenue - total_cost
        rate = flt(self.conversion_rate) or 1.0

        self.total_working_revenue = total_revenue
        self.total_working_cost = total_cost
        self.total_working_profit = total_profit

        self.total_working_revenue_base = total_revenue * rate
        self.total_working_base = total_cost * rate
        self.total_working_profit_base = total_profit * rate

        self.profit_margin_percent = (total_profit / total_revenue * 100) if total_revenue else 0

        # Optional variance fields (only if they exist on the DocType)
        if hasattr(self, "cost_variance"):
            try:
                self.cost_variance = (self.total_quoted_cost or 0) - (self.total_working_cost or 0)
            except Exception:
                pass

    def validate_customer_and_supplier(self):
        """Require party when rates are present."""
        for row in self.get("forwarding_revenue_charges", []):
            if flt(row.sell_rate) and not row.customer:
                frappe.throw(
                    _("Row {0}: Customer is required when Sell Rate is set in Revenue Charges.").format(row.idx)
                )

        for row in self.get("forwarding_cost_charges", []):
            if flt(row.buy_rate) and not row.supplier:
                frappe.throw(
                    _("Row {0}: Supplier is required when Buy Rate is set in Cost Charges.").format(row.idx)
                )

    def prevent_editing_invoiced_rows(self):
        """Disallow edits once linked to SI/PI."""
        # Revenue
        for row in self.get("forwarding_revenue_charges", []):
            if not row.name or not row.sales_invoice_reference:
                continue
            original = frappe.db.get_value(
                "Forwarding Revenue Charges", row.name, ["sell_rate", "customer", "qty"], as_dict=True
            )
            if not original:
                continue
            if (
                flt(row.sell_rate) != flt(original.sell_rate)
                or flt(row.qty) != flt(original.qty)
                or row.customer != original.customer
            ):
                frappe.throw(
                    _("You cannot change Sell Rate, Qty or Customer for Revenue row {0} already linked to Sales Invoice {1}.")
                    .format(row.idx, row.sales_invoice_reference)
                )

        # Cost
        for row in self.get("forwarding_cost_charges", []):
            if not row.name or not row.purchase_invoice_reference:
                continue
            original = frappe.db.get_value(
                "Forwarding Cost Charges", row.name, ["buy_rate", "supplier", "qty"], as_dict=True
            )
            if not original:
                continue
            if (
                flt(row.buy_rate) != flt(original.buy_rate)
                or flt(row.qty) != flt(original.qty)
                or row.supplier != original.supplier
            ):
                frappe.throw(
                    _("You cannot change Buy Rate, Qty or Supplier for Cost row {0} already linked to Purchase Invoice {1}.")
                    .format(row.idx, row.purchase_invoice_reference)
                )

    def calculate_trucks_required(self):
        """Count rows marked as is_truck_required."""
        trucks_count = 0
        for row in self.get("cargo_parcel_details", []):
            if getattr(row, "is_truck_required", 0):
                trucks_count += 1
        self.trucks_required = str(trucks_count) if trucks_count else ""

    def ensure_planned_charges_before_status_change(self):
        """Block status change from Draft -> any other unless both planned totals have amounts."""
        prev_status = None
        if self.name:
            prev_status = frappe.db.get_value("Forwarding Job", self.name, "status")

        # Treat new unsaved docs as Draft
        was_draft = (prev_status or "Draft") == "Draft"
        leaving_draft = was_draft and self.status and self.status != "Draft"

        if leaving_draft:
            rev = flt(self.total_quoted_revenue)
            cost = flt(self.total_quoted_cost)
            if rev <= 0 or cost <= 0:
                frappe.throw(_("Please add planned charges first before Starting Job. Both Planned Revenue and Planned Cost must be entered."))

    def prevent_editing_costing_charges(self):
        """Prevent add/edit/delete of forwarding_costing_charges when job is not Draft."""
        if self.status == "Draft":
            return

        # Only relevant for existing docs
        if not self.name:
            return

        # Fetch the original document from the database
        original = frappe.get_doc("Forwarding Job", self.name)
        
        original_charges = [c.as_dict() for c in original.get("forwarding_costing_charges", [])]
        current_charges = [c.as_dict() for c in self.get("forwarding_costing_charges", [])]

        # Map by name for robust comparison (allow reorder)
        orig_by_name = {r.get("name"): r for r in original_charges if r.get("name")}
        curr_by_name = {r.get("name"): r for r in current_charges if r.get("name")}

        # 1) New rows (no name) are not allowed
        for r in current_charges:
            if not r.get("name"):
                frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status. (New row detected)"))

        # 2) Deletions (a name that existed before but missing now)
        for name in orig_by_name:
            if name not in curr_by_name:
                frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status. (Row removed)"))

        # 3) Protected fields comparison on existing rows
        protected = ["charge", "qty", "sell_rate", "buy_rate", "customer", "supplier"]
        for name, orig_row in orig_by_name.items():
            curr_row = curr_by_name.get(name)
            if not curr_row:
                frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status."))

            for field in protected:
                orig_val = orig_row.get(field)
                curr_val = curr_row.get(field)

                # numeric vs string safe comparisons
                if field in ("qty", "sell_rate", "buy_rate"):
                    if flt(orig_val) != flt(curr_val):
                        frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status."))
                else:
                    if (orig_val or "") != (curr_val or ""):
                        frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status."))

    @frappe.whitelist()
    def fetch_revenue_from_costing(self):
        """
        Copy eligible revenue-side values from forwarding_costing_charges to forwarding_revenue_charges.
        
        Rules:
        - Row must have both sell_rate (> 0) and customer
        - Skip if (charge, customer) combination already exists in revenue table
        - Only copy revenue fields: charge, description, qty, sell_rate, customer, revenue_amount
        
        Returns:
            int: Number of rows added
        """
        added = 0
        
        # Build set of existing (charge, customer) combinations to avoid duplicates
        existing_revenue_pairs = set()
        for row in self.get("forwarding_revenue_charges", []):
            if row.charge and row.customer:
                existing_revenue_pairs.add((row.charge, row.customer))
        
        # Loop through costing charges and copy eligible revenue data
        for costing_row in self.get("forwarding_costing_charges", []):
            # Skip if missing required revenue fields
            if not costing_row.charge:
                continue
            if not (costing_row.customer and flt(costing_row.sell_rate)):
                continue
            
            # Skip if duplicate combination
            key = (costing_row.charge, costing_row.customer)
            if key in existing_revenue_pairs:
                continue
            
            # Calculate amounts
            qty = flt(costing_row.qty) or 1.0
            sell_rate = flt(costing_row.sell_rate)
            revenue_amount = qty * sell_rate
            
            # Add new revenue row
            self.append("forwarding_revenue_charges", {
                "charge": costing_row.charge,
                "description": costing_row.description,
                "qty": qty,
                "sell_rate": sell_rate,
                "customer": costing_row.customer,
                "revenue_amount": revenue_amount
            })
            
            existing_revenue_pairs.add(key)
            added += 1
        
        if added:
            self.save()
        
        frappe.msgprint(_("{0} revenue charge(s) added").format(added))
        return added

    @frappe.whitelist()
    def fetch_cost_from_costing(self):
        """
        Copy eligible cost-side values from forwarding_costing_charges to forwarding_cost_charges.
        
        Rules:
        - Row must have both buy_rate (> 0) and supplier
        - Skip if (charge, supplier) combination already exists in cost table
        - Only copy cost fields: charge, description, qty, buy_rate, supplier, cost_amount
        
        Returns:
            int: Number of rows added
        """
        added = 0
        
        # Build set of existing (charge, supplier) combinations to avoid duplicates
        existing_cost_pairs = set()
        for row in self.get("forwarding_cost_charges", []):
            if row.charge and row.supplier:
                existing_cost_pairs.add((row.charge, row.supplier))
        
        # Loop through costing charges and copy eligible cost data
        for costing_row in self.get("forwarding_costing_charges", []):
            # Skip if missing required cost fields
            if not costing_row.charge:
                continue
            if not (costing_row.supplier and flt(costing_row.buy_rate)):
                continue
            
            # Skip if duplicate combination
            key = (costing_row.charge, costing_row.supplier)
            if key in existing_cost_pairs:
                continue
            
            # Calculate amounts
            qty = flt(costing_row.qty) or 1.0
            buy_rate = flt(costing_row.buy_rate)
            cost_amount = qty * buy_rate
            
            # Add new cost row
            self.append("forwarding_cost_charges", {
                "charge": costing_row.charge,
                "description": costing_row.description,
                "qty": qty,
                "buy_rate": buy_rate,
                "supplier": costing_row.supplier,
                "cost_amount": cost_amount
            })
            
            existing_cost_pairs.add(key)
            added += 1
        
        if added:
            self.save()
        
        frappe.msgprint(_("{0} cost charge(s) added").format(added))
        return added

    @frappe.whitelist()
    def fetch_cost_from_truck_loading(self):
        """
        Copy truck-related costs from cargo_parcel_details to forwarding_cost_charges.
        
        Rules:
        - Only process rows where is_truck_required = 1
        - Row must have both truck_buying_rate (> 0) and transporter
        - Skip if (service_charge, transporter) combination already exists in cost table
        - Copy fields: service_charge as charge, truck_buying_rate as buy_rate, transporter as supplier
        
        Returns:
            int: Number of rows added
        """
        added = 0
        
        # Build set of existing (charge, supplier) combinations to avoid duplicates
        existing_cost_pairs = set()
        for row in self.get("forwarding_cost_charges", []):
            if row.charge and row.supplier:
                existing_cost_pairs.add((row.charge, row.supplier))
        
        # Loop through cargo parcel details and copy eligible truck cost data
        for cargo_row in self.get("cargo_parcel_details", []):
            # Skip if trucking is not required
            if not cargo_row.get("is_truck_required"):
                continue
            
            # Skip if missing required truck cost fields
            if not cargo_row.service_charge:
                continue
            if not (cargo_row.transporter and flt(cargo_row.truck_buying_rate)):
                continue
            
            # Skip if duplicate combination
            key = (cargo_row.service_charge, cargo_row.transporter)
            if key in existing_cost_pairs:
                continue
            
            # Calculate amounts (qty = 1 for truck services)
            qty = 1.0
            buy_rate = flt(cargo_row.truck_buying_rate)
            cost_amount = qty * buy_rate
            
            # Add new cost row
            self.append("forwarding_cost_charges", {
                "charge": cargo_row.service_charge,
                "description": f"Truck Loading Service - {cargo_row.service_charge}",
                "qty": qty,
                "buy_rate": buy_rate,
                "supplier": cargo_row.transporter,
                "cost_amount": cost_amount
            })
            
            existing_cost_pairs.add(key)
            added += 1
        
        if added:
            self.save()
        
        frappe.msgprint(_("{0} truck cost charge(s) added").format(added))
        return added

    def validate_cargo_milestones(self):
        """Validate cargo milestone checkboxes and dates"""
        for idx, cargo in enumerate(self.get("cargo_parcel_details", []), 1):
            if not cargo.is_truck_required:
                # Clear all milestones if trucking not required
                self.clear_cargo_milestones(cargo)
                continue
            
            # Validate sequential progression
            self.validate_milestone_sequence(cargo, idx)
            
            # Validate date consistency
            self.validate_milestone_dates(cargo, idx)
            
            # Validate required fields for specific milestones
            self.validate_milestone_requirements(cargo, idx)

    def clear_cargo_milestones(self, cargo):
        """Clear all milestone checkboxes and dates when trucking not required"""
        milestone_fields = [
            'is_booked', 'is_loaded', 'is_offloaded', 'is_returned', 'is_completed',
            'booked_on_date', 'loaded_on_date', 'offloaded_on_date', 'returned_on_date', 'completed_on_date'
        ]
        for field in milestone_fields:
            if hasattr(cargo, field):
                setattr(cargo, field, None if '_on_date' in field else 0)

    def validate_milestone_sequence(self, cargo, row_idx):
        """Ensure milestones are in proper sequence"""
        milestones = [
            ('is_booked', 'Booked'),
            ('is_loaded', 'Loaded'),
            ('is_offloaded', 'Offloaded'),
            ('is_completed', 'Completed')
        ]
        
        previous_milestone = None
        for milestone_field, milestone_label in milestones:
            current_state = getattr(cargo, milestone_field, 0)
            
            if current_state and previous_milestone and not getattr(cargo, previous_milestone[0], 0):
                frappe.throw(
                    _("Row {0}: {1} milestone cannot be completed before {2} milestone")
                    .format(row_idx, milestone_label, previous_milestone[1])
                )
            
            if current_state:
                previous_milestone = (milestone_field, milestone_label)
        
        # Validate is_returned separately (optional milestone)
        if getattr(cargo, 'is_returned', 0):
            if not getattr(cargo, 'to_be_returned', 0):
                frappe.throw(
                    _("Row {0}: Container return milestone cannot be set when 'To Be Returned' is not checked")
                    .format(row_idx)
                )
            if not getattr(cargo, 'is_offloaded', 0):
                frappe.throw(
                    _("Row {0}: Container must be offloaded before marking as returned")
                    .format(row_idx)
                )

    def validate_milestone_dates(self, cargo, row_idx):
        """Ensure milestone dates are in chronological order and not in future"""
        import datetime
        from frappe.utils import getdate, nowdate
        
        date_fields = [
            ('booked_on_date', 'Booked Date'),
            ('loaded_on_date', 'Loaded Date'),
            ('offloaded_on_date', 'Offloaded Date'),
            ('returned_on_date', 'Returned Date'),
            ('completed_on_date', 'Completed Date')
        ]
        
        dates_with_values = []
        today = getdate(nowdate())  # Use Frappe's date utilities
        
        for field, label in date_fields:
            date_value = getattr(cargo, field, None)
            if date_value:
                try:
                    # Use Frappe's getdate() to handle various date formats consistently
                    normalized_date = getdate(date_value)
                    
                    # Check for future dates
                    if normalized_date > today:
                        frappe.throw(
                            _("Row {0}: {1} cannot be in the future")
                            .format(row_idx, label)
                        )
                    
                    dates_with_values.append((field, label, normalized_date))
                    
                except Exception:
                    frappe.throw(
                        _("Row {0}: Invalid date format in {1}")
                        .format(row_idx, label)
                    )
        
        # Check chronological order
        for i in range(1, len(dates_with_values)):
            if dates_with_values[i][2] < dates_with_values[i-1][2]:
                frappe.throw(
                    _("Row {0}: {1} cannot be before {2}")
                    .format(row_idx, dates_with_values[i][1], dates_with_values[i-1][1])
                )

    def validate_milestone_requirements(self, cargo, row_idx):
        """Validate required fields for specific milestones"""
        # Required for loading
        if getattr(cargo, 'is_loaded', 0):
            if not getattr(cargo, 'driver_name', ''):
                frappe.throw(_("Row {0}: Driver name is required for loaded cargo").format(row_idx))
            if not getattr(cargo, 'driver_contact_no', ''):
                frappe.throw(_("Row {0}: Driver contact is required for loaded cargo").format(row_idx))
            if not getattr(cargo, 'truck_reg_no', ''):
                frappe.throw(_("Row {0}: Truck registration is required for loaded cargo").format(row_idx))
        
        # Required for completion
        if getattr(cargo, 'is_completed', 0):
            if not flt(getattr(cargo, 'truck_buying_rate', 0)):
                frappe.throw(_("Row {0}: Truck buying rate is required for completed cargo").format(row_idx))
            if not getattr(cargo, 'transporter', ''):
                frappe.throw(_("Row {0}: Transporter is required for completed cargo").format(row_idx))
            if not getattr(cargo, 'service_charge', ''):
                frappe.throw(_("Row {0}: Service charge is required for completed cargo").format(row_idx))

    # ========================================================
    # COMPLETION VALIDATION METHODS
    # These methods validate requirements before job status changes to Completed or before submission.
    # ========================================================

    def validate_completion_requirements(self):
        """
        Validate all requirements before job status changes to Completed.
        Checks:
        1. Actual Arrival (ata) date should be set
        2. If Direction = Import, Discharge date should be set
        3. Cargo description should be completed
        4. cargo_parcel_details table should contain at least 1 row
        5. Cargo Parcel Details validations:
           - If to_be_returned is checked, return_by_date should be set
           - If is_truck_required, road_freight_route and is_completed should be checked
        6. Tracking entries exist
        7. All working charges are invoiced
        """
        # Only validate when status is changing TO Completed
        if self.status != "Completed":
            return
        
        # Check if this is actually a status change to Completed
        prev_status = None
        if self.name:
            prev_status = frappe.db.get_value("Forwarding Job", self.name, "status")
        
        # Skip if already Completed (not a status change)
        if prev_status == "Completed":
            return
        
        errors = []
        
        # 1. Validate Actual Arrival (ata) date is set
        if not self.ata:
            errors.append(_("Actual Arrival (ATA) date must be set before completing the job"))
        
        # 2. Validate Discharge date for Import jobs
        if self.direction == "Import" and not self.discharge_date:
            errors.append(_("Discharge date must be set for Import jobs before completing"))
        
        # 3. Validate Cargo description is set
        if not self.cargo_description:
            errors.append(_("Cargo description must be completed before marking the job as Completed"))
        
        # 4. Validate at least 1 cargo parcel exists
        cargo_rows = self.get("cargo_parcel_details", [])
        if not cargo_rows:
            errors.append(_("Job must contain at least 1 cargo parcel in Cargo Parcel Details"))
        
        # 5. Validate cargo parcel details
        cargo_errors = self.check_cargo_parcel_requirements()
        if cargo_errors:
            errors.extend(cargo_errors)
        
        # 6. Validate tracking entries exist
        tracking_errors = self.check_tracking_completed()
        if tracking_errors:
            errors.extend(tracking_errors)
        
        # 7. Validate all working charges are invoiced
        invoice_errors = self.check_charges_invoiced()
        if invoice_errors:
            errors.extend(invoice_errors)
        
        # Throw all errors together
        if errors:
            error_list = "<br>".join([f"• {e}" for e in errors])
            frappe.throw(
                _("Cannot mark job as Completed. Please fix the following issues:<br><br>{0}").format(error_list),
                title=_("Completion Requirements Not Met")
            )

    def check_cargo_parcel_requirements(self):
        """
        Check cargo parcel details requirements:
        - If to_be_returned is checked, return_by_date should be set
        - If is_truck_required, road_freight_route and is_completed should be checked
        """
        errors = []
        
        cargo_rows = self.get("cargo_parcel_details", [])
        if not cargo_rows:
            return errors
        
        missing_return_date = []
        missing_route = []
        incomplete_trucking = []
        
        for idx, cargo in enumerate(cargo_rows, 1):
            row_identifier = getattr(cargo, "container_number", "") or f"Row {idx}"
            
            # Check: If to_be_returned is checked, return_by_date should be set
            if getattr(cargo, "to_be_returned", 0) and not getattr(cargo, "return_by_date", None):
                missing_return_date.append(row_identifier)
            
            # Check: If is_truck_required, road_freight_route and is_completed should be checked
            if getattr(cargo, "is_truck_required", 0):
                if not getattr(cargo, "road_freight_route", None):
                    missing_route.append(row_identifier)
                if not getattr(cargo, "is_completed", 0):
                    incomplete_trucking.append(row_identifier)
        
        # Format error messages
        if missing_return_date:
            if len(missing_return_date) <= 3:
                errors.append(_("Return By Date not set for returnable containers: {0}").format(", ".join(missing_return_date)))
            else:
                errors.append(_("{0} returnable containers are missing Return By Date").format(len(missing_return_date)))
        
        if missing_route:
            if len(missing_route) <= 3:
                errors.append(_("Road Freight Route not set for: {0}").format(", ".join(missing_route)))
            else:
                errors.append(_("{0} cargo rows requiring trucking are missing Road Freight Route").format(len(missing_route)))
        
        if incomplete_trucking:
            if len(incomplete_trucking) <= 3:
                errors.append(_("Trucking not completed for: {0}").format(", ".join(incomplete_trucking)))
            else:
                errors.append(_("{0} cargo rows requiring trucking are not marked as completed").format(len(incomplete_trucking)))
        
        return errors

    def check_tracking_completed(self):
        """Check if tracking entries exist for the job."""
        errors = []
        
        tracking_entries = self.get("forwarding_tracking", [])
        
        if not tracking_entries:
            errors.append(_("No tracking entries recorded. Please add at least one tracking update."))
        
        return errors

    def check_charges_invoiced(self):
        """Check if all working charges have been invoiced."""
        errors = []
        
        # Check revenue charges
        revenue_charges = self.get("forwarding_revenue_charges", [])
        uninvoiced_revenue = []
        for idx, charge in enumerate(revenue_charges, 1):
            if not getattr(charge, "is_invoiced", 0) and not getattr(charge, "sales_invoice_reference", None):
                charge_name = getattr(charge, "charge", "") or f"Row {idx}"
                uninvoiced_revenue.append(charge_name)
        
        if uninvoiced_revenue:
            if len(uninvoiced_revenue) <= 3:
                errors.append(_("Revenue charges not invoiced: {0}").format(", ".join(uninvoiced_revenue)))
            else:
                errors.append(_("{0} revenue charges have not been invoiced").format(len(uninvoiced_revenue)))
        
        # Check cost charges
        cost_charges = self.get("forwarding_cost_charges", [])
        uninvoiced_cost = []
        for idx, charge in enumerate(cost_charges, 1):
            if not getattr(charge, "purchase_invoice_reference", None):
                charge_name = getattr(charge, "charge", "") or f"Row {idx}"
                uninvoiced_cost.append(charge_name)
        
        if uninvoiced_cost:
            if len(uninvoiced_cost) <= 3:
                errors.append(_("Cost charges not invoiced: {0}").format(", ".join(uninvoiced_cost)))
            else:
                errors.append(_("{0} cost charges have not been invoiced").format(len(uninvoiced_cost)))
        
        return errors

    def validate_revenue_recognition_before_submit(self):
        """Validate Revenue Recognition Date is set before submission (if RR enabled)."""
        from freightmas.utils.revenue_recognition import is_revenue_recognition_enabled
        
        if is_revenue_recognition_enabled():
            if not self.revenue_recognised_on:
                frappe.throw(
                    _("Revenue Recognition Date must be set before submitting the job. "
                      "Please set the date using the 'Set Revenue Recognition Date' button."),
                    title=_("Revenue Recognition Date Required")
                )

    def get_pdf_filename(self):
        """Return custom PDF filename for Forwarding Job Cost Sheet"""
        return f"FWJB Cost Sheet {self.name}.pdf"

    # ========================================================
    # COST SHEET CALCULATION METHODS
    # These methods aggregate and format financial data for cost sheet reports and print formats.
    # Safe to delete this entire block without affecting other functionality.
    # ========================================================

    def get_all_charges_summary(self):
        """
        ========== BEGIN METHOD: get_all_charges_summary ==========
        
        Get a summary of all charges (quoted, working, invoiced) for this forwarding job.
        
        Returns a dictionary keyed by charge name with aggregated amounts:
        {
            'charge_name': {
                'quoted_revenue': amount,
                'quoted_cost': amount,
                'working_revenue': amount,
                'working_cost': amount,
                'invoiced_revenue': amount,
                'invoiced_cost': amount
            }
        }
        
        Data sources:
        - Quoted: forwarding_costing_charges table
        - Working: forwarding_revenue_charges + forwarding_cost_charges tables
        - Invoiced: Sales Invoices + Purchase Invoices linked to this job
        
        ========== END METHOD: get_all_charges_summary ==========
        """
        charges_summary = {}
        
        # Process planned/quoted charges
        if hasattr(self, 'forwarding_costing_charges') and self.forwarding_costing_charges:
            for row in self.forwarding_costing_charges:
                charge_name = row.charge
                if charge_name not in charges_summary:
                    charges_summary[charge_name] = {
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                charges_summary[charge_name]['quoted_revenue'] += flt(row.revenue_amount or 0)
                charges_summary[charge_name]['quoted_cost'] += flt(row.cost_amount or 0)
        
        # Process working/actual revenue charges
        if hasattr(self, 'forwarding_revenue_charges') and self.forwarding_revenue_charges:
            for row in self.forwarding_revenue_charges:
                charge_name = row.charge
                if charge_name not in charges_summary:
                    charges_summary[charge_name] = {
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                charges_summary[charge_name]['working_revenue'] += flt(row.revenue_amount or 0)
        
        # Process working/actual cost charges
        if hasattr(self, 'forwarding_cost_charges') and self.forwarding_cost_charges:
            for row in self.forwarding_cost_charges:
                charge_name = row.charge
                if charge_name not in charges_summary:
                    charges_summary[charge_name] = {
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                charges_summary[charge_name]['working_cost'] += flt(row.cost_amount or 0)
        
        # Process invoiced amounts from Sales Invoices (revenue)
        sales_invoices = frappe.get_all(
            'Sales Invoice',
            filters={'forwarding_job_reference': self.name, 'docstatus': 1},
            fields=['name']
        )
        
        for si in sales_invoices:
            si_doc = frappe.get_doc('Sales Invoice', si.name)
            if hasattr(si_doc, 'items') and si_doc.items:
                for item in si_doc.items:
                    charge_name = item.item_code or item.item_name
                    if charge_name not in charges_summary:
                        charges_summary[charge_name] = {
                            'quoted_revenue': 0,
                            'quoted_cost': 0,
                            'working_revenue': 0,
                            'working_cost': 0,
                            'invoiced_revenue': 0,
                            'invoiced_cost': 0
                        }
                    charges_summary[charge_name]['invoiced_revenue'] += flt(item.amount or 0)
        
        # Process invoiced amounts from Purchase Invoices (cost)
        purchase_invoices = frappe.get_all(
            'Purchase Invoice',
            filters={'forwarding_job_reference': self.name, 'docstatus': 1},
            fields=['name']
        )
        
        for pi in purchase_invoices:
            pi_doc = frappe.get_doc('Purchase Invoice', pi.name)
            if hasattr(pi_doc, 'items') and pi_doc.items:
                for item in pi_doc.items:
                    charge_name = item.item_code or item.item_name
                    if charge_name not in charges_summary:
                        charges_summary[charge_name] = {
                            'quoted_revenue': 0,
                            'quoted_cost': 0,
                            'working_revenue': 0,
                            'working_cost': 0,
                            'invoiced_revenue': 0,
                            'invoiced_cost': 0
                        }
                    charges_summary[charge_name]['invoiced_cost'] += flt(item.amount or 0)
        
        return charges_summary

    def get_all_parties_summary(self):
        """
        ========== BEGIN METHOD: get_all_parties_summary ==========
        
        Get a summary of all parties (customers/suppliers) and their charge amounts.
        
        Returns a dictionary keyed by party name with:
        {
            'party_name': {
                'party_type': 'Customer' or 'Supplier',
                'quoted_revenue': amount,
                'quoted_cost': amount,
                'working_revenue': amount,
                'working_cost': amount,
                'invoiced_revenue': amount,
                'invoiced_cost': amount
            }
        }
        
        Data sources:
        - Quoted: forwarding_costing_charges (customer/supplier fields)
        - Working: forwarding_revenue_charges (customers) + forwarding_cost_charges (suppliers)
        - Invoiced: Sales Invoices (customers) + Purchase Invoices (suppliers)
        
        ========== END METHOD: get_all_parties_summary ==========
        """
        parties_summary = {}
        
        # Process planned charges - customers
        if hasattr(self, 'forwarding_costing_charges') and self.forwarding_costing_charges:
            for row in self.forwarding_costing_charges:
                if row.customer:
                    if row.customer not in parties_summary:
                        parties_summary[row.customer] = {
                            'party_type': 'Customer',
                            'quoted_revenue': 0,
                            'quoted_cost': 0,
                            'working_revenue': 0,
                            'working_cost': 0,
                            'invoiced_revenue': 0,
                            'invoiced_cost': 0
                        }
                    parties_summary[row.customer]['quoted_revenue'] += flt(row.revenue_amount or 0)
                
                # Process planned charges - suppliers
                if row.supplier:
                    if row.supplier not in parties_summary:
                        parties_summary[row.supplier] = {
                            'party_type': 'Supplier',
                            'quoted_revenue': 0,
                            'quoted_cost': 0,
                            'working_revenue': 0,
                            'working_cost': 0,
                            'invoiced_revenue': 0,
                            'invoiced_cost': 0
                        }
                    parties_summary[row.supplier]['quoted_cost'] += flt(row.cost_amount or 0)
        
        # Process working revenue charges - customers
        if hasattr(self, 'forwarding_revenue_charges') and self.forwarding_revenue_charges:
            for row in self.forwarding_revenue_charges:
                if row.customer:
                    if row.customer not in parties_summary:
                        parties_summary[row.customer] = {
                            'party_type': 'Customer',
                            'quoted_revenue': 0,
                            'quoted_cost': 0,
                            'working_revenue': 0,
                            'working_cost': 0,
                            'invoiced_revenue': 0,
                            'invoiced_cost': 0
                        }
                    parties_summary[row.customer]['working_revenue'] += flt(row.revenue_amount or 0)
        
        # Process working cost charges - suppliers
        if hasattr(self, 'forwarding_cost_charges') and self.forwarding_cost_charges:
            for row in self.forwarding_cost_charges:
                if row.supplier:
                    if row.supplier not in parties_summary:
                        parties_summary[row.supplier] = {
                            'party_type': 'Supplier',
                            'quoted_revenue': 0,
                            'quoted_cost': 0,
                            'working_revenue': 0,
                            'working_cost': 0,
                            'invoiced_revenue': 0,
                            'invoiced_cost': 0
                        }
                    parties_summary[row.supplier]['working_cost'] += flt(row.cost_amount or 0)
        
        # Process invoiced revenue from Sales Invoices
        sales_invoices = frappe.get_all(
            'Sales Invoice',
            filters={'forwarding_job_reference': self.name, 'docstatus': 1},
            fields=['name', 'customer']
        )
        
        for si in sales_invoices:
            customer = si.customer
            if customer not in parties_summary:
                parties_summary[customer] = {
                    'party_type': 'Customer',
                    'quoted_revenue': 0,
                    'quoted_cost': 0,
                    'working_revenue': 0,
                    'working_cost': 0,
                    'invoiced_revenue': 0,
                    'invoiced_cost': 0
                }
            
            si_doc = frappe.get_doc('Sales Invoice', si.name)
            if hasattr(si_doc, 'items') and si_doc.items:
                for item in si_doc.items:
                    parties_summary[customer]['invoiced_revenue'] += flt(item.amount or 0)
        
        # Process invoiced cost from Purchase Invoices
        purchase_invoices = frappe.get_all(
            'Purchase Invoice',
            filters={'forwarding_job_reference': self.name, 'docstatus': 1},
            fields=['name', 'supplier']
        )
        
        for pi in purchase_invoices:
            supplier = pi.supplier
            if supplier not in parties_summary:
                parties_summary[supplier] = {
                    'party_type': 'Supplier',
                    'quoted_revenue': 0,
                    'quoted_cost': 0,
                    'working_revenue': 0,
                    'working_cost': 0,
                    'invoiced_revenue': 0,
                    'invoiced_cost': 0
                }
            
            pi_doc = frappe.get_doc('Purchase Invoice', pi.name)
            if hasattr(pi_doc, 'items') and pi_doc.items:
                for item in pi_doc.items:
                    parties_summary[supplier]['invoiced_cost'] += flt(item.amount or 0)
        
        return parties_summary

    def get_job_totals_summary(self):
        """
        ========== BEGIN METHOD: get_job_totals_summary ==========
        
        Get overall totals and margin metrics for this forwarding job.
        
        Returns a dictionary with:
        {
            'quoted_revenue': total,
            'quoted_cost': total,
            'quoted_margin': margin,
            'quoted_margin_percent': percent,
            'working_revenue': total,
            'working_cost': total,
            'working_margin': margin,
            'working_margin_percent': percent,
            'invoiced_revenue': total,
            'invoiced_cost': total,
            'invoiced_margin': margin,
            'invoiced_margin_percent': percent
        }
        
        Calculates:
        - Quoted totals: from forwarding_costing_charges
        - Working totals: from forwarding_revenue_charges + forwarding_cost_charges
        - Invoiced totals: from Sales Invoices + Purchase Invoices
        - Margins: calculated as Revenue - Cost
        - Margin percentages: (Margin / Revenue) * 100
        
        ========== END METHOD: get_job_totals_summary ==========
        """
        quoted_revenue = flt(self.total_quoted_revenue or 0)
        quoted_cost = flt(self.total_quoted_cost or 0)
        working_revenue = flt(self.total_working_revenue or 0)
        working_cost = flt(self.total_working_cost or 0)
        
        # Get invoiced totals
        invoiced_revenue = 0
        invoiced_cost = 0
        
        sales_invoices = frappe.get_all(
            'Sales Invoice',
            filters={'forwarding_job_reference': self.name, 'docstatus': 1},
            fields=['total']
        )
        invoiced_revenue = sum([flt(si.get('total', 0)) for si in sales_invoices])
        
        purchase_invoices = frappe.get_all(
            'Purchase Invoice',
            filters={'forwarding_job_reference': self.name, 'docstatus': 1},
            fields=['total']
        )
        invoiced_cost = sum([flt(pi.get('total', 0)) for pi in purchase_invoices])
        
        quoted_margin = quoted_revenue - quoted_cost
        working_margin = working_revenue - working_cost
        invoiced_margin = invoiced_revenue - invoiced_cost
        
        quoted_margin_percent = (quoted_margin / quoted_revenue * 100) if quoted_revenue > 0 else 0
        working_margin_percent = (working_margin / working_revenue * 100) if working_revenue > 0 else 0
        invoiced_margin_percent = (invoiced_margin / invoiced_revenue * 100) if invoiced_revenue > 0 else 0
        
        return {
            'quoted_revenue': quoted_revenue,
            'quoted_cost': quoted_cost,
            'quoted_margin': quoted_margin,
            'quoted_margin_percent': quoted_margin_percent,
            'working_revenue': working_revenue,
            'working_cost': working_cost,
            'working_margin': working_margin,
            'working_margin_percent': working_margin_percent,
            'invoiced_revenue': invoiced_revenue,
            'invoiced_cost': invoiced_cost,
            'invoiced_margin': invoiced_margin,
            'invoiced_margin_percent': invoiced_margin_percent
        }

    def get_charge_details_for_cost_sheet(self):
        """
        ========== BEGIN METHOD: get_charge_details_for_cost_sheet ==========
        
        Get organized charge details formatted specifically for cost sheet templates.
        This is the primary method called by print formats to display charge data.
        
        Returns:
        {
            'charges': [
                {
                    'charge': name,
                    'quoted_revenue': amount,
                    'quoted_cost': amount,
                    'working_revenue': amount,
                    'working_cost': amount,
                    'invoiced_revenue': amount,
                    'invoiced_cost': amount
                }
            ],
            'totals': {
                'quoted_revenue': total,
                'quoted_cost': total,
                'working_revenue': total,
                'working_cost': total,
                'invoiced_revenue': total,
                'invoiced_cost': total,
                'invoiced_margin': margin
            }
        }
        
        Usage in print format:
            {% set data = doc.get_charge_details_for_cost_sheet() %}
            {% for charge in data.charges %}
                {{ charge.charge }}: {{ charge.quoted_revenue }}
            {% endfor %}
        
        ========== END METHOD: get_charge_details_for_cost_sheet ==========
        """
        charges_summary = self.get_all_charges_summary()
        totals = self.get_job_totals_summary()
        
        charges_list = []
        for charge_name, amounts in charges_summary.items():
            charges_list.append({
                'charge': charge_name,
                'quoted_revenue': amounts['quoted_revenue'],
                'quoted_cost': amounts['quoted_cost'],
                'working_revenue': amounts['working_revenue'],
                'working_cost': amounts['working_cost'],
                'invoiced_revenue': amounts['invoiced_revenue'],
                'invoiced_cost': amounts['invoiced_cost']
            })
        
        return {
            'charges': sorted(charges_list, key=lambda x: x['charge']),
            'totals': {
                'quoted_revenue': totals['quoted_revenue'],
                'quoted_cost': totals['quoted_cost'],
                'working_revenue': totals['working_revenue'],
                'working_cost': totals['working_cost'],
                'invoiced_revenue': totals['invoiced_revenue'],
                'invoiced_cost': totals['invoiced_cost'],
                'invoiced_margin': totals['invoiced_margin']
            }
        }

    def get_party_details_for_cost_sheet(self):
        """
        ========== BEGIN METHOD: get_party_details_for_cost_sheet ==========
        
        Get organized party (customer/supplier) details formatted for cost sheet templates.
        This is the primary method called by print formats to display party data.
        
        Returns:
        {
            'customers': [
                {
                    'party': name,
                    'quoted_revenue': amount,
                    'quoted_cost': amount,
                    'working_revenue': amount,
                    'working_cost': amount,
                    'invoiced_revenue': amount,
                    'invoiced_cost': amount
                }
            ],
            'suppliers': [
                {
                    'party': name,
                    'quoted_revenue': amount,
                    'quoted_cost': amount,
                    'working_revenue': amount,
                    'working_cost': amount,
                    'invoiced_revenue': amount,
                    'invoiced_cost': amount
                }
            ],
            'totals': {
                'quoted_revenue': total,
                'quoted_cost': total,
                'working_revenue': total,
                'working_cost': total,
                'invoiced_revenue': total,
                'invoiced_cost': total
            }
        }
        
        Usage in print format:
            {% set data = doc.get_party_details_for_cost_sheet() %}
            <h3>Customers</h3>
            {% for customer in data.customers %}
                {{ customer.party }}: {{ customer.quoted_revenue }}
            {% endfor %}
            <h3>Suppliers</h3>
            {% for supplier in data.suppliers %}
                {{ supplier.party }}: {{ supplier.quoted_cost }}
            {% endfor %}
        
        ========== END METHOD: get_party_details_for_cost_sheet ==========
        """
        parties_summary = self.get_all_parties_summary()
        
        customers = []
        suppliers = []
        
        for party_name, amounts in parties_summary.items():
            party_data = {
                'party': party_name,
                'quoted_revenue': amounts['quoted_revenue'],
                'quoted_cost': amounts['quoted_cost'],
                'working_revenue': amounts['working_revenue'],
                'working_cost': amounts['working_cost'],
                'invoiced_revenue': amounts['invoiced_revenue'],
                'invoiced_cost': amounts['invoiced_cost']
            }
            
            if amounts['party_type'] == 'Customer':
                customers.append(party_data)
            else:
                suppliers.append(party_data)
        
        totals = self.get_job_totals_summary()
        
        return {
            'customers': sorted(customers, key=lambda x: x['party']),
            'suppliers': sorted(suppliers, key=lambda x: x['party']),
            'totals': {
                'quoted_revenue': totals['quoted_revenue'],
                'quoted_cost': totals['quoted_cost'],
                'working_revenue': totals['working_revenue'],
                'working_cost': totals['working_cost'],
                'invoiced_revenue': totals['invoiced_revenue'],
                'invoiced_cost': totals['invoiced_cost']
            }
        }

    # ========================================================
    # END COST SHEET CALCULATION METHODS
    # Safe to delete entire block above without affecting other code.
    # ========================================================


# ========================================================
# SALES INVOICE CREATION - UPDATED for forwarding_revenue_charges
# ========================================================
@frappe.whitelist()
def create_sales_invoice_with_rows(docname, row_names):
    # row_names can be JSON string from client
    if isinstance(row_names, str):
        row_names = frappe.parse_json(row_names) or []

    job = frappe.get_doc("Forwarding Job", docname)

    selected_rows = [row for row in job.get("forwarding_revenue_charges", []) if row.name in row_names]
    if not selected_rows:
        frappe.throw(_("No valid revenue charge rows were selected."))

    # All rows must belong to same customer
    customers = {r.customer for r in selected_rows if r.customer}
    if len(customers) != 1:
        frappe.throw(_("Please select rows for a single Customer."))

    customer = list(customers)[0]
    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    
    # Optional custom fields (ignore if missing)
    try:
        if si.meta.get_field("forwarding_job_reference"):
            si.forwarding_job_reference = job.name
    except Exception:
        pass
    
    try:
        if si.meta.get_field("is_forwarding_invoice"):
            si.is_forwarding_invoice = 1
    except Exception:
        pass

    si.set_posting_time = 1
    si.posting_date = nowdate()
    if getattr(job, "currency", None):
        si.currency = job.currency
    if getattr(job, "conversion_rate", None):
        si.conversion_rate = job.conversion_rate

    cargo_desc = job.get("cargo_description") or "N/A"
    customer_ref = job.get("customer_reference") or "N/A"
    si.remarks = f"Forwarding Job {job.name}, Reference {customer_ref}, Cargo: {cargo_desc}"

    # Get WIP Revenue account if revenue recognition is enabled
    wip_revenue_account = None
    try:
        from freightmas.utils.revenue_recognition import (
            is_revenue_recognition_enabled,
            get_wip_revenue_account,
        )
        if is_revenue_recognition_enabled():
            wip_revenue_account = get_wip_revenue_account()
    except Exception:
        pass

    for row in selected_rows:
        item_dict = {
            "item_code": row.charge,
            "description": row.description or row.charge,
            "qty": row.qty or 1,
            "rate": row.sell_rate or 0,
        }
        # Force WIP Revenue account if revenue recognition is enabled
        if wip_revenue_account:
            item_dict["income_account"] = wip_revenue_account
        
        si.append("items", item_dict)

    si.insert()

    # Mark rows as invoiced
    for row in job.get("forwarding_revenue_charges", []):
        if row.name in row_names:
            row.is_invoiced = 1
            row.sales_invoice_reference = si.name

    job.save()
    return si.name

# ========================================================
# PURCHASE INVOICE CREATION - UPDATED for forwarding_cost_charges
# ========================================================
@frappe.whitelist()
def create_purchase_invoice_with_rows(docname, row_names):
    if isinstance(row_names, str):
        row_names = frappe.parse_json(row_names) or []

    job = frappe.get_doc("Forwarding Job", docname)

    selected_rows = [row for row in job.get("forwarding_cost_charges", []) if row.name in row_names]
    if not selected_rows:
        frappe.throw(_("No valid cost charge rows were selected."))

    suppliers = {r.supplier for r in selected_rows if r.supplier}
    if len(suppliers) != 1:
        frappe.throw(_("Please select rows for a single Supplier."))

    supplier = list(suppliers)[0]
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = supplier
    
    # Optional custom fields (ignore if missing)
    try:
        if pi.meta.get_field("forwarding_job_reference"):
            pi.forwarding_job_reference = job.name
    except Exception:
        pass
    
    try:
        if pi.meta.get_field("is_forwarding_invoice"):
            pi.is_forwarding_invoice = 1
    except Exception:
        pass

    pi.set_posting_time = 1
    pi.posting_date = nowdate()
    if getattr(job, "currency", None):
        pi.currency = job.currency
    if getattr(job, "conversion_rate", None):
        pi.conversion_rate = job.conversion_rate

    # Get supplier invoice details from selected rows (use first available)
    supplier_inv_no = None
    supplier_inv_date = None
    for row in selected_rows:
        if not supplier_inv_no and row.get("supplier_invoice_no"):
            supplier_inv_no = row.supplier_invoice_no
        if not supplier_inv_date and row.get("supplier_invoice_date"):
            supplier_inv_date = row.supplier_invoice_date
        if supplier_inv_no and supplier_inv_date:
            break

    # Set bill_no and bill_date on Purchase Invoice
    if supplier_inv_no:
        pi.bill_no = supplier_inv_no
    if supplier_inv_date:
        pi.bill_date = supplier_inv_date

    customer_ref = job.get("customer_reference") or "N/A"
    supplier_inv_display = supplier_inv_no or "N/A"
    pi.remarks = f"Forwarding Job {job.name}, Ref: {customer_ref}, Invoice: {supplier_inv_display}"

    for row in selected_rows:
        pi.append(
            "items",
            {
                "item_code": row.charge,
                "description": row.description or row.charge,
                "qty": row.qty or 1,
                "rate": row.buy_rate or 0,
            },
        )

    pi.insert()

    # Mark rows as purchased
    for row in job.get("forwarding_cost_charges", []):
        if row.name in row_names:
            row.is_purchased = 1
            row.purchase_invoice_reference = pi.name

    job.save()
    return pi.name

    def get_pdf_filename(self):
        """Return custom PDF filename for Forwarding Job Cost Sheet"""
        return f"FWJB Cost Sheet {self.name}.pdf"


