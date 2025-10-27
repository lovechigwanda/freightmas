# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, cint
from frappe import _

class ForwardingJob(Document):
    
    def validate(self):
        """Validate document before saving"""
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

    def set_base_currency(self):
        if not self.base_currency and self.company:
            self.base_currency = frappe.db.get_value("Company", self.company, "default_currency")
        if not self.conversion_rate:
            self.conversion_rate = 1.0

    def calculate_costing_charges(self):
        """Calculate amounts for each costing charge line"""
        for charge in self.get("forwarding_costing_charges", []):
            # Get quantity (default to 1)
            qty = flt(charge.qty) if charge.qty else 1
            
            # Calculate revenue amount (sell side)
            sell_rate = flt(charge.sell_rate)
            charge.revenue_amount = qty * sell_rate
            
            # Calculate cost amount (buy side)
            buy_rate = flt(charge.buy_rate)
            charge.cost_amount = qty * buy_rate
            
            # Calculate margin
            charge.margin_amount = charge.revenue_amount - charge.cost_amount
            
            # Calculate margin percentage
            if charge.revenue_amount > 0:
                charge.margin_percentage = (charge.margin_amount / charge.revenue_amount) * 100
            else:
                charge.margin_percentage = 0
    
    def calculate_costing_totals(self):
        """Calculate total estimated revenue, cost and profit from costing charges"""
        total_revenue = 0
        total_cost = 0
        
        # Sum all costing charges
        for charge in self.get("forwarding_costing_charges", []):
            total_revenue += flt(charge.revenue_amount)
            total_cost += flt(charge.cost_amount)
        
        total_profit = total_revenue - total_cost
        rate = flt(self.conversion_rate) or 1.0
        
        # Update totals in transaction currency
        self.total_estimated_revenue = total_revenue
        self.total_estimated_cost = total_cost
        self.total_estimated_profit = total_profit
        
        # Update totals in base currency
        self.total_estimated_revenue_base = total_revenue * rate
        self.total_estimated_cost_base = total_cost * rate
        self.total_estimated_profit_base = total_profit * rate
        
        # Calculate profit margin percentage
        if total_revenue > 0:
            self.estimated_profit_margin_percent = (total_profit / total_revenue) * 100
        else:
            self.estimated_profit_margin_percent = 0
    
    def calculate_actual_revenue_charges(self):
        """Calculate amounts for each actual revenue charge line"""
        for charge in self.get("forwarding_revenue_charges", []):
            # Get quantity (default to 1)
            qty = flt(charge.qty) if charge.qty else 1
            
            # Calculate revenue amount
            sell_rate = flt(charge.sell_rate)
            charge.revenue_amount = qty * sell_rate
    
    def calculate_actual_cost_charges(self):
        """Calculate amounts for each actual cost charge line"""
        for charge in self.get("forwarding_cost_charges", []):
            # Get quantity (default to 1)
            qty = flt(charge.qty) if charge.qty else 1
            
            # Calculate cost amount
            buy_rate = flt(charge.buy_rate)
            charge.cost_amount = qty * buy_rate
    
    def calculate_actual_totals(self):
        """Calculate total actual revenue, cost and profit - EXACTLY like costing totals"""
        # Calculate revenue totals
        total_revenue = 0
        
        for charge in self.get("forwarding_revenue_charges", []):
            total_revenue += flt(charge.revenue_amount)
        
        # Calculate cost totals
        total_cost = 0
        
        for charge in self.get("forwarding_cost_charges", []):
            total_cost += flt(charge.cost_amount)
        
        # Calculate profit
        total_profit = total_revenue - total_cost
        
        # Get conversion rate (same as costing)
        rate = flt(self.conversion_rate) or 1.0
        
        # Update actual totals in transaction currency
        self.total_txn_revenue = total_revenue
        self.total_txn_cost = total_cost
        self.total_txn_profit = total_profit
        
        # Update actual totals in base currency
        self.total_txn_revenue_base = total_revenue * rate
        self.total_txn_base = total_cost * rate  # Note: field name is total_txn_base for cost
        self.total_txn_profit_base = total_profit * rate
        
        # Calculate profit margin percentage - EXACTLY like costing
        if total_revenue > 0:
            self.profit_margin_percent = (total_profit / total_revenue) * 100
        else:
            self.profit_margin_percent = 0
        
        # Calculate variances (optional, if fields exist)
        if hasattr(self, 'cost_variance'):
            self.cost_variance = total_cost - flt(self.total_estimated_cost)
            self.revenue_variance = total_revenue - flt(self.total_estimated_revenue)
            self.profit_variance = total_profit - flt(self.total_estimated_profit)
            
            # Calculate variance percentages
            if self.total_estimated_cost > 0:
                self.cost_variance_percent = (self.cost_variance / self.total_estimated_cost) * 100
            else:
                self.cost_variance_percent = 0
            
            if self.total_estimated_revenue > 0:
                self.revenue_variance_percent = (self.revenue_variance / self.total_estimated_revenue) * 100
            else:
                self.revenue_variance_percent = 0
            
            if self.total_estimated_profit > 0:
                self.profit_variance_percent = (self.profit_variance / self.total_estimated_profit) * 100
            else:
                self.profit_variance_percent = 0

    def calculate_totals(self):
        total_revenue = 0
        total_cost = 0

        for row in self.forwarding_charges:
            row.revenue_amount = flt(row.qty) * flt(row.sell_rate)
            row.cost_amount = flt(row.qty) * flt(row.buy_rate)
            total_revenue += flt(row.revenue_amount)
            total_cost += flt(row.cost_amount)

        total_profit = total_revenue - total_cost
        rate = flt(self.conversion_rate)

        self.total_estimated_revenue = total_revenue
        self.total_estimated_cost = total_cost
        self.total_estimated_profit = total_profit

        self.total_estimated_revenue_base = total_revenue * rate
        self.total_estimated_cost_base = total_cost * rate
        self.total_estimated_profit_base = total_profit * rate

    def validate_customer_and_supplier(self):
        for row in self.forwarding_charges:
            if row.sell_rate and not row.customer:
                frappe.throw(
                    _("Customer is required for row {0} because Sell Rate is entered.").format(row.idx),
                    title="Missing Customer"
                )
            if row.buy_rate and not row.supplier:
                frappe.throw(
                    _("Supplier is required for row {0} because Buy Rate is entered.").format(row.idx),
                    title="Missing Supplier"
                )

    def prevent_editing_invoiced_rows(self):
        for row in self.forwarding_charges:
            if not row.name or row.name.startswith("NEW-"):
                continue

            if not (row.sales_invoice_reference or row.purchase_invoice_reference):
                continue

            try:
                original = frappe.get_doc("Forwarding Charges", row.name)
            except frappe.DoesNotExistError:
                continue

            if row.sales_invoice_reference:
                for field in ["sell_rate", "customer", "qty"]:
                    if row.get(field) != original.get(field):
                        frappe.throw(
                            f"You cannot modify '{field}' on a charge already linked to Sales Invoice: {row.sales_invoice_reference}"
                        )

            if row.purchase_invoice_reference:
                for field in ["buy_rate", "supplier", "qty"]:
                    if row.get(field) != original.get(field):
                        frappe.throw(
                            f"You cannot modify '{field}' on a charge already linked to Purchase Invoice: {row.purchase_invoice_reference}"
                        )

    def calculate_trucks_required(self):
        """Calculate the number of trucks required based on cargo parcel details"""
        trucks_count = 0
        for row in self.cargo_parcel_details:
            if row.is_truck_required:
                trucks_count += 1
        
        self.trucks_required = str(trucks_count) if trucks_count > 0 else ""


# ========================================================
# SALES INVOICE CREATION - UPDATED for forwarding_revenue_charges
# ========================================================

@frappe.whitelist()
def create_sales_invoice_with_rows(docname, row_names):
    import json
    if isinstance(row_names, str):
        row_names = json.loads(row_names)

    job = frappe.get_doc("Forwarding Job", docname)
    
    # Use forwarding_revenue_charges instead of forwarding_charges
    selected_rows = [row for row in job.forwarding_revenue_charges if row.name in row_names]

    if not selected_rows:
        frappe.throw("No valid revenue charges selected.")

    si = frappe.new_doc("Sales Invoice")
    si.customer = selected_rows[0].customer
    si.forwarding_job_reference = job.name
    si.is_forwarding_invoice = 1
    si.set_posting_time = 1
    si.posting_date = nowdate()
    si.currency = job.currency
    si.conversion_rate = job.conversion_rate or 1

    cargo_desc = job.cargo_description or "N/A"
    charge_list = ", ".join([row.charge for row in selected_rows])
    si.remarks = f"Forwarding Job {job.name} (Cargo: {cargo_desc}): {charge_list}"

    for row in selected_rows:
        si.append("items", {
            "item_code": row.charge,
            "description": row.description or row.charge,
            "qty": row.qty or 1,
            "rate": row.sell_rate
        })

    si.insert()

    # Update forwarding_revenue_charges table (not forwarding_charges)
    for row in job.forwarding_revenue_charges:
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
    import json
    if isinstance(row_names, str):
        row_names = json.loads(row_names)

    job = frappe.get_doc("Forwarding Job", docname)
    
    # Use forwarding_cost_charges instead of forwarding_charges
    selected_rows = [row for row in job.forwarding_cost_charges if row.name in row_names]

    if not selected_rows:
        frappe.throw("No valid cost charges selected.")

    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = selected_rows[0].supplier
    pi.forwarding_job_reference = job.name
    pi.is_forwarding_invoice = 1
    pi.set_posting_time = 1
    pi.posting_date = nowdate()
    pi.currency = job.currency
    pi.conversion_rate = job.conversion_rate or 1

    cargo_desc = job.cargo_description or "N/A"
    charge_list = ", ".join([row.charge for row in selected_rows])
    pi.remarks = f"Forwarding Job {job.name} (Cargo: {cargo_desc}): {charge_list}"

    for row in selected_rows:
        pi.append("items", {
            "item_code": row.charge,
            "description": row.description or row.charge,
            "qty": row.qty or 1,
            "rate": row.buy_rate
        })

    pi.insert()

    # Update forwarding_cost_charges table (not forwarding_charges)
    for row in job.forwarding_cost_charges:
        if row.name in row_names:
            row.is_purchased = 1
            row.purchase_invoice_reference = pi.name

    job.save()
    return pi.name
