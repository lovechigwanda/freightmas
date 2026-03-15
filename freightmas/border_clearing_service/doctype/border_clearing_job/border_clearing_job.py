# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, cint
from frappe import _
from freightmas.utils.permissions import check_doc_read_permission


class BorderClearingJob(Document):

    def validate(self):
        """Validate document before saving"""
        if self.status == "Completed" and not self.completed_on:
            self.completed_on = nowdate()

        self.set_base_currency()

        # Calculate costing charges
        self.calculate_costing_charges()
        self.calculate_costing_totals()

        # Calculate actual charges
        self.calculate_actual_revenue_charges()
        self.calculate_actual_cost_charges()
        self.calculate_actual_totals()

        # Update tracking info
        self.update_last_tracking()

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

        self.validate_revenue_recognition_before_submit()

        from freightmas.utils.revenue_recognition import recognize_revenue_for_job, recognize_cost_for_job
        recognize_revenue_for_job(self, "border_clearing")
        recognize_cost_for_job(self, "border_clearing")

    def on_cancel(self):
        """Handle job cancellation - reverse revenue and cost recognition"""
        from freightmas.utils.revenue_recognition import reverse_revenue_recognition, reverse_cost_recognition
        reverse_revenue_recognition(self)
        reverse_cost_recognition(self)

    # ========================================================
    # CURRENCY
    # ========================================================

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

    # ========================================================
    # COSTING CALCULATIONS
    # ========================================================

    def calculate_costing_charges(self):
        """Compute line amounts for costing table."""
        for charge in self.get("border_clearing_costing_charges", []):
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
        """Totals for costing section, with separate pass-through tracking."""
        total_revenue = 0
        total_cost = 0
        total_pass_through = 0

        for charge in self.get("border_clearing_costing_charges", []):
            total_revenue += flt(charge.revenue_amount)
            total_cost += flt(charge.cost_amount)
            if cint(charge.is_pass_through):
                total_pass_through += flt(charge.revenue_amount)

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
        self.total_quoted_duty_pass_through = total_pass_through

    # ========================================================
    # ACTUAL REVENUE / COST CALCULATIONS
    # ========================================================

    def calculate_actual_revenue_charges(self):
        """Compute line amounts for actual revenue table."""
        for charge in self.get("border_clearing_revenue_charges", []):
            qty = flt(charge.qty) or 1
            sell_rate = flt(charge.sell_rate) or 0
            charge.revenue_amount = qty * sell_rate

    def calculate_actual_cost_charges(self):
        """Compute line amounts for actual cost table."""
        for charge in self.get("border_clearing_cost_charges", []):
            qty = flt(charge.qty) or 1
            buy_rate = flt(charge.buy_rate) or 0
            charge.cost_amount = qty * buy_rate

    def calculate_actual_totals(self):
        """Totals for actual section, with separate pass-through tracking."""
        total_revenue = 0
        total_pass_through = 0
        for charge in self.get("border_clearing_revenue_charges", []):
            total_revenue += flt(charge.revenue_amount)
            if cint(charge.is_pass_through):
                total_pass_through += flt(charge.revenue_amount)

        total_cost = 0
        for charge in self.get("border_clearing_cost_charges", []):
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
        self.total_working_duty_pass_through = total_pass_through

    # ========================================================
    # TRACKING
    # ========================================================

    def update_last_tracking(self):
        """Update current_comment, last_updated_by, last_updated_on from latest tracking row."""
        tracking = self.get("border_clearing_tracking", [])
        if tracking:
            last = tracking[-1]
            self.current_comment = last.comment
            self.last_updated_by = last.updated_by
            self.last_updated_on = last.updated_on

    # ========================================================
    # VALIDATIONS
    # ========================================================

    def validate_customer_and_supplier(self):
        """Require party when rates are present."""
        for row in self.get("border_clearing_revenue_charges", []):
            if flt(row.sell_rate) and not row.customer:
                frappe.throw(
                    _("Row {0}: Customer is required when Sell Rate is set in Revenue Charges.").format(row.idx)
                )

        for row in self.get("border_clearing_cost_charges", []):
            if flt(row.buy_rate) and not row.supplier:
                frappe.throw(
                    _("Row {0}: Supplier is required when Buy Rate is set in Cost Charges.").format(row.idx)
                )

    def prevent_editing_invoiced_rows(self):
        """Disallow edits once linked to SI/PI."""
        for row in self.get("border_clearing_revenue_charges", []):
            if not row.name or not row.sales_invoice_reference:
                continue
            original = frappe.db.get_value(
                "Border Clearing Revenue Charges", row.name,
                ["sell_rate", "customer", "qty"], as_dict=True
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

        for row in self.get("border_clearing_cost_charges", []):
            if not row.name or not row.purchase_invoice_reference:
                continue
            original = frappe.db.get_value(
                "Border Clearing Cost Charges", row.name,
                ["buy_rate", "supplier", "qty"], as_dict=True
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
            prev_status = frappe.db.get_value("Border Clearing Job", self.name, "status")

        was_draft = (prev_status or "Draft") == "Draft"
        leaving_draft = was_draft and self.status and self.status != "Draft"

        if leaving_draft:
            rev = flt(self.total_quoted_revenue)
            cost = flt(self.total_quoted_cost)
            if rev <= 0 or cost <= 0:
                frappe.throw(
                    _("Please add planned charges first before Starting Job. "
                      "Both Planned Revenue and Planned Cost must be entered.")
                )

    def prevent_editing_costing_charges(self):
        """Prevent add/edit/delete of costing charges when job is not Draft."""
        if self.status == "Draft":
            return
        if not self.name:
            return

        original = frappe.get_doc("Border Clearing Job", self.name)
        original_charges = [c.as_dict() for c in original.get("border_clearing_costing_charges", [])]
        current_charges = [c.as_dict() for c in self.get("border_clearing_costing_charges", [])]

        orig_by_name = {r.get("name"): r for r in original_charges if r.get("name")}
        curr_by_name = {r.get("name"): r for r in current_charges if r.get("name")}

        for r in current_charges:
            if not r.get("name"):
                frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status. (New row detected)"))

        for name in orig_by_name:
            if name not in curr_by_name:
                frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status. (Row removed)"))

        protected = ["charge", "qty", "sell_rate", "buy_rate", "customer", "supplier", "is_pass_through"]
        for name, orig_row in orig_by_name.items():
            curr_row = curr_by_name.get(name)
            if not curr_row:
                frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status."))

            for field in protected:
                orig_val = orig_row.get(field)
                curr_val = curr_row.get(field)
                if field in ("qty", "sell_rate", "buy_rate"):
                    if flt(orig_val) != flt(curr_val):
                        frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status."))
                elif field == "is_pass_through":
                    if cint(orig_val) != cint(curr_val):
                        frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status."))
                else:
                    if (orig_val or "") != (curr_val or ""):
                        frappe.throw(_("Planned Job Costing cannot be modified after the job leaves Draft status."))

    def validate_completion_requirements(self):
        """Validate all requirements before job status changes to Completed."""
        if self.status != "Completed":
            return

        prev_status = None
        if self.name:
            prev_status = frappe.db.get_value("Border Clearing Job", self.name, "status")

        if prev_status == "Completed":
            return

        errors = []

        # Milestones
        if not self.is_documents_received:
            errors.append(_("Documents must be marked as received"))
        if not self.is_entry_lodged:
            errors.append(_("Entry must be marked as lodged"))
        if not self.is_duty_assessed:
            errors.append(_("Duty must be marked as assessed"))
        if not self.is_duty_paid:
            errors.append(_("Duty must be marked as paid"))
        if not self.is_release_obtained:
            errors.append(_("Release must be obtained"))
        if not self.is_cleared:
            errors.append(_("Goods must be marked as cleared"))

        # Examination: if required, must be done
        if self.is_examination_required and not self.is_examination_done:
            errors.append(_("Examination is required but not completed"))

        # Tracking entries
        if not self.get("border_clearing_tracking", []):
            errors.append(_("No tracking entries recorded. Please add at least one tracking update."))

        # All working charges invoiced
        invoice_errors = self.check_charges_invoiced()
        if invoice_errors:
            errors.extend(invoice_errors)

        if errors:
            error_list = "<br>".join([f"• {e}" for e in errors])
            frappe.throw(
                _("Cannot mark job as Completed. Please fix the following issues:<br><br>{0}").format(error_list),
                title=_("Completion Requirements Not Met")
            )

    def check_charges_invoiced(self):
        """Check if all working charges have been invoiced."""
        errors = []

        uninvoiced_revenue = []
        for idx, charge in enumerate(self.get("border_clearing_revenue_charges", []), 1):
            if not getattr(charge, "is_invoiced", 0) and not getattr(charge, "sales_invoice_reference", None):
                charge_name = getattr(charge, "charge", "") or f"Row {idx}"
                uninvoiced_revenue.append(charge_name)

        if uninvoiced_revenue:
            if len(uninvoiced_revenue) <= 3:
                errors.append(_("Revenue charges not invoiced: {0}").format(", ".join(uninvoiced_revenue)))
            else:
                errors.append(_("{0} revenue charges have not been invoiced").format(len(uninvoiced_revenue)))

        uninvoiced_cost = []
        for idx, charge in enumerate(self.get("border_clearing_cost_charges", []), 1):
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

    # ========================================================
    # FETCH FROM COSTING
    # ========================================================

    @frappe.whitelist()
    def fetch_revenue_from_costing(self):
        """Copy eligible revenue-side values from costing to revenue charges (including is_pass_through)."""
        added = 0

        existing_revenue_pairs = set()
        for row in self.get("border_clearing_revenue_charges", []):
            if row.charge and row.customer:
                existing_revenue_pairs.add((row.charge, row.customer))

        for costing_row in self.get("border_clearing_costing_charges", []):
            if not costing_row.charge:
                continue
            if not (costing_row.customer and flt(costing_row.sell_rate)):
                continue

            key = (costing_row.charge, costing_row.customer)
            if key in existing_revenue_pairs:
                continue

            qty = flt(costing_row.qty) or 1.0
            sell_rate = flt(costing_row.sell_rate)
            revenue_amount = qty * sell_rate

            self.append("border_clearing_revenue_charges", {
                "charge": costing_row.charge,
                "description": costing_row.description,
                "qty": qty,
                "sell_rate": sell_rate,
                "customer": costing_row.customer,
                "revenue_amount": revenue_amount,
                "is_pass_through": cint(costing_row.is_pass_through),
            })

            existing_revenue_pairs.add(key)
            added += 1

        if added:
            self.save()

        frappe.msgprint(_("{0} revenue charge(s) added").format(added))
        return added

    @frappe.whitelist()
    def fetch_cost_from_costing(self):
        """Copy eligible cost-side values from costing to cost charges (including is_pass_through)."""
        added = 0

        existing_cost_pairs = set()
        for row in self.get("border_clearing_cost_charges", []):
            if row.charge and row.supplier:
                existing_cost_pairs.add((row.charge, row.supplier))

        for costing_row in self.get("border_clearing_costing_charges", []):
            if not costing_row.charge:
                continue
            if not (costing_row.supplier and flt(costing_row.buy_rate)):
                continue

            key = (costing_row.charge, costing_row.supplier)
            if key in existing_cost_pairs:
                continue

            qty = flt(costing_row.qty) or 1.0
            buy_rate = flt(costing_row.buy_rate)
            cost_amount = qty * buy_rate

            self.append("border_clearing_cost_charges", {
                "charge": costing_row.charge,
                "description": costing_row.description,
                "qty": qty,
                "buy_rate": buy_rate,
                "supplier": costing_row.supplier,
                "cost_amount": cost_amount,
                "is_pass_through": cint(costing_row.is_pass_through),
            })

            existing_cost_pairs.add(key)
            added += 1

        if added:
            self.save()

        frappe.msgprint(_("{0} cost charge(s) added").format(added))
        return added

    # ========================================================
    # COST SHEET METHODS
    # ========================================================

    def get_pdf_filename(self):
        return f"BCJB Cost Sheet {self.name}.pdf"

    def get_all_charges_summary(self):
        """Get a summary of all charges for cost sheet."""
        charges_summary = {}

        for row in self.get("border_clearing_costing_charges", []):
            charge_name = row.charge
            if charge_name not in charges_summary:
                charges_summary[charge_name] = {
                    "quoted_revenue": 0, "quoted_cost": 0,
                    "working_revenue": 0, "working_cost": 0,
                    "invoiced_revenue": 0, "invoiced_cost": 0,
                    "is_pass_through": cint(row.is_pass_through),
                }
            charges_summary[charge_name]["quoted_revenue"] += flt(row.revenue_amount)
            charges_summary[charge_name]["quoted_cost"] += flt(row.cost_amount)

        for row in self.get("border_clearing_revenue_charges", []):
            charge_name = row.charge
            if charge_name not in charges_summary:
                charges_summary[charge_name] = {
                    "quoted_revenue": 0, "quoted_cost": 0,
                    "working_revenue": 0, "working_cost": 0,
                    "invoiced_revenue": 0, "invoiced_cost": 0,
                    "is_pass_through": cint(row.is_pass_through),
                }
            charges_summary[charge_name]["working_revenue"] += flt(row.revenue_amount)

        for row in self.get("border_clearing_cost_charges", []):
            charge_name = row.charge
            if charge_name not in charges_summary:
                charges_summary[charge_name] = {
                    "quoted_revenue": 0, "quoted_cost": 0,
                    "working_revenue": 0, "working_cost": 0,
                    "invoiced_revenue": 0, "invoiced_cost": 0,
                    "is_pass_through": cint(row.is_pass_through),
                }
            charges_summary[charge_name]["working_cost"] += flt(row.cost_amount)

        return charges_summary

    def get_job_totals_summary(self):
        """Get overall totals and margin metrics."""
        quoted_revenue = flt(self.total_quoted_revenue)
        quoted_cost = flt(self.total_quoted_cost)
        working_revenue = flt(self.total_working_revenue)
        working_cost = flt(self.total_working_cost)

        quoted_margin = quoted_revenue - quoted_cost
        working_margin = working_revenue - working_cost

        return {
            "quoted_revenue": quoted_revenue,
            "quoted_cost": quoted_cost,
            "quoted_margin": quoted_margin,
            "quoted_margin_percent": (quoted_margin / quoted_revenue * 100) if quoted_revenue else 0,
            "working_revenue": working_revenue,
            "working_cost": working_cost,
            "working_margin": working_margin,
            "working_margin_percent": (working_margin / working_revenue * 100) if working_revenue else 0,
        }


# ========================================================
# SALES INVOICE CREATION
# ========================================================
@frappe.whitelist()
def create_sales_invoice_with_rows(docname, row_names):
    check_doc_read_permission("Border Clearing Job", docname)
    if isinstance(row_names, str):
        row_names = frappe.parse_json(row_names) or []

    job = frappe.get_doc("Border Clearing Job", docname)

    selected_rows = [row for row in job.get("border_clearing_revenue_charges", []) if row.name in row_names]
    if not selected_rows:
        frappe.throw(_("No valid revenue charge rows were selected."))
    if any(row.sales_invoice_reference for row in selected_rows):
        frappe.throw(_("One or more selected rows are already linked to a Sales Invoice. Please refresh and try again."))

    customers = {r.customer for r in selected_rows if r.customer}
    if len(customers) != 1:
        frappe.throw(_("Please select rows for a single Customer."))

    customer = list(customers)[0]
    si = frappe.new_doc("Sales Invoice")
    si.customer = customer

    try:
        if si.meta.get_field("custom_border_clearing_job"):
            si.custom_border_clearing_job = job.name
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

    # Get pass-through account
    pass_through_account = frappe.db.get_single_value("FreightMas Settings", "duty_pass_through_account")

    for row in selected_rows:
        item_dict = {
            "item_code": row.charge,
            "description": row.description or row.charge,
            "qty": row.qty or 1,
            "rate": row.sell_rate or 0,
        }
        # Pass-through rows use clearing account instead of income
        if cint(row.is_pass_through) and pass_through_account:
            item_dict["income_account"] = pass_through_account
        elif wip_revenue_account:
            item_dict["income_account"] = wip_revenue_account

        si.append("items", item_dict)

    si.insert()

    for row in job.get("border_clearing_revenue_charges", []):
        if row.name in row_names:
            row.is_invoiced = 1
            row.sales_invoice_reference = si.name

    job.save()
    return si.name


# ========================================================
# PURCHASE INVOICE CREATION
# ========================================================
@frappe.whitelist()
def create_purchase_invoice_with_rows(docname, row_names):
    check_doc_read_permission("Border Clearing Job", docname)
    if isinstance(row_names, str):
        row_names = frappe.parse_json(row_names) or []

    job = frappe.get_doc("Border Clearing Job", docname)

    selected_rows = [row for row in job.get("border_clearing_cost_charges", []) if row.name in row_names]
    if not selected_rows:
        frappe.throw(_("No valid cost charge rows were selected."))

    suppliers = {r.supplier for r in selected_rows if r.supplier}
    if len(suppliers) != 1:
        frappe.throw(_("Please select rows for a single Supplier."))

    supplier = list(suppliers)[0]
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = supplier

    try:
        if pi.meta.get_field("custom_border_clearing_job"):
            pi.custom_border_clearing_job = job.name
    except Exception:
        pass

    pi.set_posting_time = 1
    pi.posting_date = nowdate()
    if getattr(job, "currency", None):
        pi.currency = job.currency
    if getattr(job, "conversion_rate", None):
        pi.conversion_rate = job.conversion_rate

    # Get supplier invoice details from selected rows
    supplier_inv_no = None
    supplier_inv_date = None
    for row in selected_rows:
        if not supplier_inv_no and row.get("supplier_invoice_no"):
            supplier_inv_no = row.supplier_invoice_no
        if not supplier_inv_date and row.get("supplier_invoice_date"):
            supplier_inv_date = row.supplier_invoice_date
        if supplier_inv_no and supplier_inv_date:
            break

    if supplier_inv_no:
        pi.bill_no = supplier_inv_no
    if supplier_inv_date:
        pi.bill_date = supplier_inv_date

    customer_ref = job.get("customer_reference") or "N/A"
    supplier_inv_display = supplier_inv_no or "N/A"
    pi.remarks = f"{job.name}, Ref: {customer_ref}, Inv: {supplier_inv_display}"

    # Get pass-through account
    pass_through_account = frappe.db.get_single_value("FreightMas Settings", "duty_pass_through_account")

    for row in selected_rows:
        item_dict = {
            "item_code": row.charge,
            "description": row.description or row.charge,
            "qty": row.qty or 1,
            "rate": row.buy_rate or 0,
        }
        # Pass-through rows use clearing account instead of expense
        if cint(row.is_pass_through) and pass_through_account:
            item_dict["expense_account"] = pass_through_account

        pi.append("items", item_dict)

    pi.insert()

    for row in job.get("border_clearing_cost_charges", []):
        if row.name in row_names:
            row.is_purchased = 1
            row.purchase_invoice_reference = pi.name

    job.save()
    return pi.name
