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
