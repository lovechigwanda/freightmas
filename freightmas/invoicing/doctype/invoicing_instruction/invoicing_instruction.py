# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime
from frappe import _


class InvoicingInstruction(Document):

    def validate(self):
        """Validate document before saving."""
        self.calculate_totals()

    def on_submit(self):
        """
        On submit:
        1. Set status to Submitted
        2. Create an Invoice Register Entry with status = Instruction Received
        """
        self.db_set("status", "Submitted")

        # Create the corresponding Register Entry
        register_entry = frappe.get_doc({
            "doctype": "Invoice Register Entry",
            "entry_type": "Sales",
            "company": self.company,
            "job_doctype": "Forwarding Job",
            "job_name": self.forwarding_job,
            "party_type": "Customer",
            "party": self.customer,
            "currency": self.currency,
            "amount": self.total_amount,
            "linked_invoicing_instruction": self.name,
            "received_on": now_datetime(),
            "notes": self.notes or "",
        })

        # Fetch conversion_rate from the Job
        conversion_rate = frappe.db.get_value(
            "Forwarding Job", self.forwarding_job, "conversion_rate"
        )
        if conversion_rate:
            register_entry.conversion_rate = flt(conversion_rate)

        register_entry.insert(ignore_permissions=True)

        # Link back
        self.db_set("linked_register_entry", register_entry.name)

        frappe.msgprint(
            _("Invoice Register Entry {0} created").format(
                frappe.utils.get_link_to_form(
                    "Invoice Register Entry", register_entry.name
                )
            ),
            alert=True,
        )

    def on_cancel(self):
        """On cancel: set status to Cancelled."""
        self.db_set("status", "Cancelled")

        # If a register entry was created but not yet actioned, cancel it too
        if self.linked_register_entry:
            entry = frappe.get_doc("Invoice Register Entry", self.linked_register_entry)
            if entry.status == "Instruction Received":
                entry.change_status("Cancelled", comment="Invoicing Instruction cancelled")

    def calculate_totals(self):
        """Calculate total amount and item count from line items."""
        total = 0
        count = 0
        for item in self.get("line_items", []):
            qty = flt(item.qty) or 1
            rate = flt(item.sell_rate)
            item.amount = flt(qty * rate, 2)
            total += item.amount
            count += 1

        self.total_amount = flt(total, 2)
        self.total_items = count

    @frappe.whitelist()
    def fetch_charges_from_job(self):
        """
        Pull uninvoiced revenue charges from the linked Forwarding Job
        as a snapshot into the Instruction's line_items.

        Returns:
            int: Number of rows added.
        """
        if not self.forwarding_job:
            frappe.throw(_("Please select a Forwarding Job first"))

        job = frappe.get_doc("Forwarding Job", self.forwarding_job)
        added = 0

        # Track already-added source rows
        existing_sources = set()
        for item in self.get("line_items", []):
            if item.source_charge_row:
                existing_sources.add(item.source_charge_row)

        for charge in job.get("forwarding_revenue_charges", []):
            # Skip already invoiced or already added
            if charge.is_invoiced or charge.sales_invoice_reference:
                continue
            if charge.name in existing_sources:
                continue
            if not charge.charge or not flt(charge.sell_rate):
                continue

            qty = flt(charge.qty) or 1
            sell_rate = flt(charge.sell_rate)

            self.append("line_items", {
                "charge": charge.charge,
                "description": charge.description,
                "qty": qty,
                "sell_rate": sell_rate,
                "amount": flt(qty * sell_rate, 2),
                "customer": charge.customer or job.customer,
                "source_charge_row": charge.name,
            })
            added += 1

        if added:
            self.calculate_totals()
            self.save()

        frappe.msgprint(_("{0} charge(s) added from {1}").format(added, self.forwarding_job))
        return added
