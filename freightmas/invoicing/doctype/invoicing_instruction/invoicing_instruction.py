# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime
from frappe import _


class InvoicingInstruction(Document):

    def validate(self):
        self.calculate_totals()

    def on_submit(self):
        """
        On submit:
        1. Set status to Submitted.
        2. Create a Sales Invoice Register Entry (status = Instruction Received).
        3. Copy line items into the register entry's charge_details for a full breakdown.
        4. Link both documents back to each other.
        """
        self.db_set("status", "Submitted")

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

        conversion_rate = frappe.db.get_value(
            "Forwarding Job", self.forwarding_job, "conversion_rate"
        )
        if conversion_rate:
            register_entry.conversion_rate = flt(conversion_rate)

        # Issue 9 fix: copy line items as charge_details so the register entry
        # carries a full line-item breakdown, not just the header total.
        for item in self.get("line_items", []):
            if not item.charge:
                continue
            register_entry.append("charge_details", {
                "charge": item.charge,
                "description": item.description,
                "qty": flt(item.qty) or 1,
                "rate": flt(item.sell_rate),
                "line_amount": flt(item.amount),
                "line_party_type": "Customer",
                "line_party": item.customer or self.customer,
            })

        register_entry.insert(ignore_permissions=True)

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
        """
        On cancel:
        1. Mark this instruction as Cancelled.
        2. If the linked register entry is still at its initial state, cancel it
           too using direct db_set calls — avoids triggering the full save/validate
           chain inside an ongoing cancel hook.
        """
        self.db_set("status", "Cancelled")

        if not self.linked_register_entry:
            return

        entry_status = frappe.db.get_value(
            "Invoice Register Entry", self.linked_register_entry, "status"
        )
        if entry_status != "Instruction Received":
            return

        # Issue 6 fix: use db_set instead of entry.change_status() → entry.save()
        # to avoid running the full validate chain inside a cancel hook.
        frappe.db.set_value(
            "Invoice Register Entry",
            self.linked_register_entry,
            {
                "status": "Cancelled",
                "current_status_since": now_datetime(),
                "is_overdue": 0,
                "sla_due_at": None,
            },
        )

        frappe.msgprint(
            _("Invoice Register Entry {0} also cancelled.").format(
                frappe.utils.get_link_to_form(
                    "Invoice Register Entry", self.linked_register_entry
                )
            ),
            alert=True,
        )

    def mark_as_actioned(self, sales_invoice):
        """
        Mark this instruction as Actioned once the Sales Invoice has been raised.

        Called by InvoiceRegisterEntry.notify_instruction_on_invoice_link() when
        linked_sales_invoice is first populated on the associated register entry.
        Uses db_set to avoid triggering submit/amend validation on an already-submitted doc.
        """
        self.db_set({
            "status": "Actioned",
            "linked_sales_invoice": sales_invoice,
            "actioned_by": frappe.session.user,
            "actioned_on": now_datetime(),
        })

    def calculate_totals(self):
        """Calculate total amount and item count from line items."""
        total = 0.0
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

        existing_sources = {
            item.source_charge_row
            for item in self.get("line_items", [])
            if item.source_charge_row
        }

        for charge in job.get("forwarding_revenue_charges", []):
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
