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

        self.total_estimated_revenue = total_revenue
        self.total_estimated_cost = total_cost
        self.total_estimated_profit = total_profit

        self.total_estimated_revenue_base = total_revenue * rate
        self.total_estimated_cost_base = total_cost * rate
        self.total_estimated_profit_base = total_profit * rate

        self.estimated_profit_margin_percent = (
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

        self.total_txn_revenue = total_revenue
        self.total_txn_cost = total_cost
        self.total_txn_profit = total_profit

        self.total_txn_revenue_base = total_revenue * rate
        self.total_txn_base = total_cost * rate
        self.total_txn_profit_base = total_profit * rate

        self.profit_margin_percent = (total_profit / total_revenue * 100) if total_revenue else 0

        # Optional variance fields (only if they exist on the DocType)
        if hasattr(self, "cost_variance"):
            try:
                self.cost_variance = (self.total_estimated_cost or 0) - (self.total_txn_cost or 0)
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
            rev = flt(self.total_estimated_revenue)
            cost = flt(self.total_estimated_cost)
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
    charge_list = ", ".join([row.charge for row in selected_rows if row.charge])
    si.remarks = f"Forwarding Job {job.name} (Cargo: {cargo_desc}): {charge_list}"

    for row in selected_rows:
        si.append(
            "items",
            {
                "item_code": row.charge,
                "description": row.description or row.charge,
                "qty": row.qty or 1,
                "rate": row.sell_rate or 0,
            },
        )

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

    cargo_desc = job.get("cargo_description") or "N/A"
    charge_list = ", ".join([row.charge for row in selected_rows if row.charge])
    pi.remarks = f"Forwarding Job {job.name} (Cargo: {cargo_desc}): {charge_list}"

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

