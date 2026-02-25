# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, cint
from frappe import _
from freightmas.utils.permissions import check_doc_read_permission

class ClearingJob(Document):

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

        # Skip validations if checkbox is ticked (for cancelling problematic jobs)
        if self.skip_validations:
            if "System Manager" not in frappe.get_roles():
                frappe.throw(_("Only System Managers can use Skip Validations"))
        else:
            self.validate_customer_and_supplier()
            self.prevent_editing_invoiced_rows()
            self.ensure_planned_charges_before_status_change()
            self.prevent_editing_costing_charges()
            self.validate_completion_requirements()

    def on_submit(self):
        """Handle job submission - trigger revenue and cost recognition"""
        if self.skip_validations:
            return

        # Validate Revenue Recognition Date before proceeding
        self.validate_revenue_recognition_before_submit()

        from freightmas.utils.revenue_recognition import recognize_revenue_for_job, recognize_cost_for_job
        recognize_revenue_for_job(self, "clearing")
        recognize_cost_for_job(self, "clearing")

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
        for charge in self.get("clearing_costing_charges", []):
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

        for charge in self.get("clearing_costing_charges", []):
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
        for charge in self.get("clearing_revenue_charges", []):
            qty = flt(charge.qty) or 1
            sell_rate = flt(charge.sell_rate) or 0
            charge.revenue_amount = qty * sell_rate

    def calculate_actual_cost_charges(self):
        """Compute line amounts for actual cost table."""
        for charge in self.get("clearing_cost_charges", []):
            qty = flt(charge.qty) or 1
            buy_rate = flt(charge.buy_rate) or 0
            charge.cost_amount = qty * buy_rate

    def calculate_actual_totals(self):
        """Totals for actual section."""
        total_revenue = 0
        for charge in self.get("clearing_revenue_charges", []):
            total_revenue += flt(charge.revenue_amount)

        total_cost = 0
        for charge in self.get("clearing_cost_charges", []):
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

    def validate_customer_and_supplier(self):
        """Require party when rates are present."""
        for row in self.get("clearing_revenue_charges", []):
            if flt(row.sell_rate) and not row.customer:
                frappe.throw(
                    _("Row {0}: Customer is required when Sell Rate is set in Revenue Charges.").format(row.idx)
                )

        for row in self.get("clearing_cost_charges", []):
            if flt(row.buy_rate) and not row.supplier:
                frappe.throw(
                    _("Row {0}: Supplier is required when Buy Rate is set in Cost Charges.").format(row.idx)
                )

    def prevent_editing_invoiced_rows(self):
        """Disallow edits once linked to SI/PI."""
        # Revenue
        for row in self.get("clearing_revenue_charges", []):
            if not row.name or not row.sales_invoice_reference:
                continue
            original = frappe.db.get_value(
                "Clearing Revenue Charges", row.name, ["sell_rate", "customer", "qty"], as_dict=True
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
        for row in self.get("clearing_cost_charges", []):
            if not row.name or not row.purchase_invoice_reference:
                continue
            original = frappe.db.get_value(
                "Clearing Cost Charges", row.name, ["buy_rate", "supplier", "qty"], as_dict=True
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

    def ensure_planned_charges_before_status_change(self):
        """Block status change from Draft -> any other unless both planned totals have amounts."""
        prev_status = None
        if self.name:
            prev_status = frappe.db.get_value("Clearing Job", self.name, "status")

        # Treat new unsaved docs as Draft
        was_draft = (prev_status or "Draft") == "Draft"
        leaving_draft = was_draft and self.status and self.status != "Draft"

        if leaving_draft:
            rev = flt(self.total_quoted_revenue)
            cost = flt(self.total_quoted_cost)
            if rev <= 0 or cost <= 0:
                frappe.throw(_("Please add planned charges first before Starting Job. Both Planned Revenue and Planned Cost must be entered."))

    def prevent_editing_costing_charges(self):
        """Prevent add/edit/delete of clearing_costing_charges when job is not Draft."""
        if self.status == "Draft":
            return

        # Only relevant for existing docs
        if not self.name:
            return

        # Fetch the original document from the database
        original = frappe.get_doc("Clearing Job", self.name)

        original_charges = [c.as_dict() for c in original.get("clearing_costing_charges", [])]
        current_charges = [c.as_dict() for c in self.get("clearing_costing_charges", [])]

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
        Copy eligible revenue-side values from clearing_costing_charges to clearing_revenue_charges.

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
        for row in self.get("clearing_revenue_charges", []):
            if row.charge and row.customer:
                existing_revenue_pairs.add((row.charge, row.customer))

        # Loop through costing charges and copy eligible revenue data
        for costing_row in self.get("clearing_costing_charges", []):
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
            self.append("clearing_revenue_charges", {
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
        Copy eligible cost-side values from clearing_costing_charges to clearing_cost_charges.

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
        for row in self.get("clearing_cost_charges", []):
            if row.charge and row.supplier:
                existing_cost_pairs.add((row.charge, row.supplier))

        # Loop through costing charges and copy eligible cost data
        for costing_row in self.get("clearing_costing_charges", []):
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
            self.append("clearing_cost_charges", {
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

    # ========================================================
    # COMPLETION VALIDATION METHODS
    # ========================================================

    def validate_completion_requirements(self):
        """
        Validate all requirements before job status changes to Completed.
        Checks:
        1. For Import: ATA date should be set; For Export: ATD date should be set
        2. If Direction = Import, Discharge date should be set
        3. BL number must be set, BL received and confirmed
        4. Import milestones (vessel arrived, SL invoice, DO, clearing, port discharge)
        5. Export milestones (booking, loading, sailing, port release)
        6. Cargo description should be completed
        7. Cargo package details must have at least 1 row
        8. Tracking entries exist
        9. All working charges are invoiced
        """
        # Only validate when status is changing TO Completed
        if self.status != "Completed":
            return

        # Check if this is actually a status change to Completed
        prev_status = None
        if self.name:
            prev_status = frappe.db.get_value("Clearing Job", self.name, "status")

        # Skip if already Completed (not a status change)
        if prev_status == "Completed":
            return

        errors = []

        # 1. Validate arrival/departure dates based on direction
        if self.direction == "Import" and not self.ata:
            errors.append(_("Actual Arrival (ATA) date must be set before completing the job"))
        elif self.direction == "Export" and not self.atd:
            errors.append(_("Actual Departure (ATD) date must be set before completing the job"))

        # 2. Validate Discharge date for Import jobs
        if self.direction == "Import" and not self.discharge_date:
            errors.append(_("Discharge date must be set for Import jobs before completing"))

        # 3. Validate BL & Documents
        if not self.bl_number:
            errors.append(_("Bill of Lading (BL) number must be set before completing the job"))
        if not self.is_bl_received:
            errors.append(_("Bill of Lading must be marked as received"))
        if not self.is_bl_confirmed:
            errors.append(_("Bill of Lading must be marked as confirmed"))

        # 4. Validate Import milestones
        if self.direction == "Import":
            if not self.is_vessel_arrived_at_port:
                errors.append(_("Vessel Arrived at Port must be confirmed"))
            if not self.is_sl_invoice_received:
                errors.append(_("Shipping Line invoice must be marked as received"))
            if not self.is_sl_invoice_paid:
                errors.append(_("Shipping Line invoice must be marked as paid"))
            if not self.is_do_requested:
                errors.append(_("Delivery Order must be marked as requested"))
            if not self.is_do_received:
                errors.append(_("Delivery Order must be marked as received"))
            if not self.is_clearing_for_shipment_done:
                errors.append(_("Clearing for shipment must be marked as done"))
            if not self.is_discharged_from_port:
                errors.append(_("Cargo must be marked as discharged from port"))

        # 5. Validate Export milestones
        if self.direction == "Export":
            if not self.is_booking_confirmed:
                errors.append(_("Booking with Shipping Line must be confirmed"))
            if not self.is_loaded_on_vessel:
                errors.append(_("Cargo must be marked as loaded on vessel"))
            if not self.is_vessel_sailed:
                errors.append(_("Vessel must be marked as sailed"))
            if not self.is_port_release_confirmed:
                errors.append(_("Port release must be confirmed"))

        # 6. Validate Cargo description is set
        if not self.cargo_description:
            errors.append(_("Cargo description must be completed before marking the job as Completed"))

        # 7. Validate at least 1 cargo package exists
        cargo_rows = self.get("cargo_package_details", [])
        if not cargo_rows:
            errors.append(_("Job must contain at least 1 row in Cargo Package Details"))

        # 8. Validate tracking entries exist
        tracking_errors = self.check_tracking_completed()
        if tracking_errors:
            errors.extend(tracking_errors)

        # 9. Validate all working charges are invoiced
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

    def check_tracking_completed(self):
        """Check if tracking entries exist for the job."""
        errors = []

        tracking_entries = self.get("clearing_tracking", [])

        if not tracking_entries:
            errors.append(_("No tracking entries recorded. Please add at least one tracking update."))

        return errors

    def check_charges_invoiced(self):
        """Check if all working charges have been invoiced."""
        errors = []

        # Check revenue charges
        revenue_charges = self.get("clearing_revenue_charges", [])
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
        cost_charges = self.get("clearing_cost_charges", [])
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
        """Return custom PDF filename for Clearing Job Cost Sheet"""
        return f"CLJB Cost Sheet {self.name}.pdf"

    # ========================================================
    # COST SHEET CALCULATION METHODS
    # ========================================================

    def get_all_charges_summary(self):
        """
        Get a summary of all charges (quoted, working, invoiced) for this clearing job.

        Returns a dictionary keyed by charge name with aggregated amounts.
        """
        charges_summary = {}

        # Process planned/quoted charges
        if hasattr(self, 'clearing_costing_charges') and self.clearing_costing_charges:
            for row in self.clearing_costing_charges:
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
        if hasattr(self, 'clearing_revenue_charges') and self.clearing_revenue_charges:
            for row in self.clearing_revenue_charges:
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
        if hasattr(self, 'clearing_cost_charges') and self.clearing_cost_charges:
            for row in self.clearing_cost_charges:
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
            filters={'clearing_job_reference': self.name, 'docstatus': 1},
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
            filters={'clearing_job_reference': self.name, 'docstatus': 1},
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
        Get a summary of all parties (customers/suppliers) and their charge amounts.
        """
        parties_summary = {}

        # Process planned charges - customers
        if hasattr(self, 'clearing_costing_charges') and self.clearing_costing_charges:
            for row in self.clearing_costing_charges:
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
        if hasattr(self, 'clearing_revenue_charges') and self.clearing_revenue_charges:
            for row in self.clearing_revenue_charges:
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
        if hasattr(self, 'clearing_cost_charges') and self.clearing_cost_charges:
            for row in self.clearing_cost_charges:
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
            filters={'clearing_job_reference': self.name, 'docstatus': 1},
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
            filters={'clearing_job_reference': self.name, 'docstatus': 1},
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
        Get overall totals and margin metrics for this clearing job.
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
            filters={'clearing_job_reference': self.name, 'docstatus': 1},
            fields=['total']
        )
        invoiced_revenue = sum([flt(si.get('total', 0)) for si in sales_invoices])

        purchase_invoices = frappe.get_all(
            'Purchase Invoice',
            filters={'clearing_job_reference': self.name, 'docstatus': 1},
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
        Get organized charge details formatted specifically for cost sheet templates.
        This is the primary method called by print formats to display charge data.
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
        Get organized party (customer/supplier) details formatted for cost sheet templates.
        This is the primary method called by print formats to display party data.
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
# SALES INVOICE CREATION - for clearing_revenue_charges
# ========================================================
@frappe.whitelist()
def create_sales_invoice_with_rows(docname, row_names):
    check_doc_read_permission("Clearing Job", docname)
    # row_names can be JSON string from client
    if isinstance(row_names, str):
        row_names = frappe.parse_json(row_names) or []

    job = frappe.get_doc("Clearing Job", docname)

    selected_rows = [row for row in job.get("clearing_revenue_charges", []) if row.name in row_names]
    if not selected_rows:
        frappe.throw(_("No valid revenue charge rows were selected."))
    if any(row.sales_invoice_reference for row in selected_rows):
        frappe.throw(_("One or more selected rows are already linked to a Sales Invoice. Please refresh and try again."))

    # All rows must belong to same customer
    customers = {r.customer for r in selected_rows if r.customer}
    if len(customers) != 1:
        frappe.throw(_("Please select rows for a single Customer."))

    customer = list(customers)[0]
    si = frappe.new_doc("Sales Invoice")
    si.customer = customer

    # Optional custom fields (ignore if missing)
    try:
        if si.meta.get_field("clearing_job_reference"):
            si.clearing_job_reference = job.name
    except Exception:
        pass

    try:
        if si.meta.get_field("is_clearing_invoice"):
            si.is_clearing_invoice = 1
    except Exception:
        pass

    si.set_posting_time = 1
    si.posting_date = nowdate()
    if getattr(job, "currency", None):
        si.currency = job.currency
    if getattr(job, "conversion_rate", None):
        si.conversion_rate = job.conversion_rate

    customer_ref = job.get("customer_reference") or "N/A"
    cargo_desc = job.get("cargo_description") or "N/A"
    si.remarks = f"{job.name}, Ref: {customer_ref}, {cargo_desc}"

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
    for row in job.get("clearing_revenue_charges", []):
        if row.name in row_names:
            row.is_invoiced = 1
            row.sales_invoice_reference = si.name

    job.save()
    return si.name

# ========================================================
# PURCHASE INVOICE CREATION - for clearing_cost_charges
# ========================================================
@frappe.whitelist()
def create_purchase_invoice_with_rows(docname, row_names):
    check_doc_read_permission("Clearing Job", docname)
    if isinstance(row_names, str):
        row_names = frappe.parse_json(row_names) or []

    job = frappe.get_doc("Clearing Job", docname)

    selected_rows = [row for row in job.get("clearing_cost_charges", []) if row.name in row_names]
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
        if pi.meta.get_field("clearing_job_reference"):
            pi.clearing_job_reference = job.name
    except Exception:
        pass

    try:
        if pi.meta.get_field("is_clearing_invoice"):
            pi.is_clearing_invoice = 1
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
    pi.remarks = f"{job.name}, Ref: {customer_ref}, Inv: {supplier_inv_display}"

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
    for row in job.get("clearing_cost_charges", []):
        if row.name in row_names:
            row.is_purchased = 1
            row.purchase_invoice_reference = pi.name

    job.save()
    return pi.name
