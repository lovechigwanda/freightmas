# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, nowdate
from frappe import _


# ========================================================
# VALID TRANSITIONS PER ENTRY TYPE
# ========================================================

PURCHASE_TRANSITIONS = {
    "Received": ["Submitted for Approval", "Cancelled"],
    "Submitted for Approval": ["Returned for Capture", "Query with Supplier"],
    "Query with Supplier": ["Ready for Capture", "Cancelled"],
    "Ready for Capture": ["Captured"],
    "Returned for Capture": ["Captured"],
    "Captured": [],
    "Cancelled": [],
}

SALES_TRANSITIONS = {
    "Instruction Received": ["Drafted", "Cancelled"],
    "Drafted": ["Issued to Client", "Returned to Draft"],
    "Returned to Draft": ["Drafted"],
    "Issued to Client": [],
    "Cancelled": [],
}

# States that require a comment in the status log
COMMENT_REQUIRED_STATES = {"Query with Supplier", "Returned to Draft", "Cancelled"}

# Terminal states — no further transitions allowed
TERMINAL_STATES = {"Captured", "Issued to Client", "Cancelled"}

LOCKED_STATUSES = {"Captured", "Issued to Client"}

LOCKED_PARENT_FIELDS = {
    "company": "Company",
    "entry_type": "Entry Type",
    "entry_date": "Entry Date",
    "status": "Status",
    "job_doctype": "Job Type",
    "job_name": "Job",
    "party_type": "Party Type",
    "party": "Party",
    "currency": "Currency",
    "conversion_rate": "Exchange Rate",
    "amount": "Amount",
    "amount_base": "Amount (Base Currency)",
    "tax_amount": "Tax Amount",
    "base_currency": "Base Currency",
    "total_charge_amount": "Total Charge Amount",
    "supplier_invoice_no": "Supplier Invoice No",
    "supplier_invoice_date": "Supplier Invoice Date",
    "linked_purchase_invoice": "Purchase Invoice",
    "linked_sales_invoice": "Sales Invoice",
}

LOCKED_CHILD_FIELDS = (
    "charge",
    "description",
    "qty",
    "rate",
    "line_amount",
    "line_party_type",
    "line_party",
    "attachment",
)

NUMERIC_LOCKED_FIELDS = {
    "conversion_rate",
    "amount",
    "amount_base",
    "tax_amount",
    "total_charge_amount",
}

NUMERIC_CHILD_FIELDS = {"qty", "rate", "line_amount"}


class InvoiceRegisterEntry(Document):

    def validate(self):
        """Validate document before saving."""
        self.set_party_type_from_entry_type()
        self.calculate_charge_totals()
        self.compute_base_amount()
        self.validate_job_reference()
        self.validate_locked_entry()

    def on_trash(self):
        """Prevent deletion after the entry has produced an actual invoice."""
        if self.is_locked():
            frappe.throw(self.get_locked_message(), title=_("Invoice Register Entry Locked"))

    def before_insert(self):
        """Set initial status and timestamps on creation."""
        if not self.status:
            if self.entry_type == "Purchase":
                self.status = "Received"
            elif self.entry_type == "Sales":
                self.status = "Instruction Received"

        if not self.received_on:
            self.received_on = now_datetime()

        self.current_status_since = now_datetime()

    def set_party_type_from_entry_type(self):
        """Auto-set party_type based on entry_type."""
        if self.entry_type == "Sales" and self.party_type != "Customer":
            self.party_type = "Customer"
        elif self.entry_type == "Purchase" and self.party_type != "Supplier":
            self.party_type = "Supplier"

    def compute_base_amount(self):
        """Compute base currency amount from transaction amount and exchange rate."""
        rate = flt(self.conversion_rate) or 1.0
        self.amount_base = flt(flt(self.amount) * rate, 2)

    def validate_job_reference(self):
        """Ensure the job reference exists and fetch company if not set."""
        if self.job_doctype and self.job_name:
            if not frappe.db.exists(self.job_doctype, self.job_name):
                frappe.throw(
                    _("{0} {1} does not exist").format(self.job_doctype, self.job_name)
                )
            # Auto-fetch company from Job if not set
            if not self.company:
                self.company = frappe.db.get_value(
                    self.job_doctype, self.job_name, "company"
                )

    def is_locked(self):
        """Return true when the register entry should no longer be edited."""
        return (
            self.status in LOCKED_STATUSES
            or bool(self.linked_purchase_invoice)
            or bool(self.linked_sales_invoice)
        )

    def get_locked_message(self):
        """Build a clear reason for the lock."""
        if self.linked_purchase_invoice:
            return _(
                "Invoice Register Entry {0} is locked because Purchase Invoice {1} has already been raised."
            ).format(self.name, frappe.bold(self.linked_purchase_invoice))
        if self.linked_sales_invoice:
            return _(
                "Invoice Register Entry {0} is locked because Sales Invoice {1} has already been raised."
            ).format(self.name, frappe.bold(self.linked_sales_invoice))
        return _("Invoice Register Entry {0} is locked because its status is {1}.").format(
            self.name, frappe.bold(self.status)
        )

    def validate_locked_entry(self):
        """
        Freeze business fields once the saved entry is already captured or linked.

        The transition into a locked state is allowed; edits after that point are blocked.
        """
        if self.is_new():
            return

        original = self.get_doc_before_save()
        if not original or not original.is_locked():
            return

        changed_fields = []
        for fieldname, label in LOCKED_PARENT_FIELDS.items():
            if self.has_locked_field_changed(original, fieldname):
                changed_fields.append(label)

        if self.has_charge_details_changed(original):
            changed_fields.append(_("Charges"))

        if changed_fields:
            frappe.throw(
                _("{0}<br><br>The following field(s) cannot be changed after capture: {1}").format(
                    self.get_locked_message(), ", ".join(changed_fields)
                ),
                title=_("Invoice Register Entry Locked"),
            )

    def has_locked_field_changed(self, original, fieldname):
        """Compare locked parent fields with currency/float tolerance."""
        current_value = self.get(fieldname)
        original_value = original.get(fieldname)

        if fieldname in NUMERIC_LOCKED_FIELDS:
            return flt(current_value) != flt(original_value)

        return (current_value or "") != (original_value or "")

    def has_charge_details_changed(self, original):
        """Detect add/remove/edit/reorder in charge rows."""
        return self.get_locked_charge_snapshot(self) != self.get_locked_charge_snapshot(original)

    def get_locked_charge_snapshot(self, doc):
        """Create a comparable representation of charge rows."""
        snapshot = []
        for row in doc.get("charge_details", []):
            row_data = {
                "name": row.name,
                "idx": row.idx,
            }
            for fieldname in LOCKED_CHILD_FIELDS:
                value = row.get(fieldname)
                if fieldname in NUMERIC_CHILD_FIELDS:
                    value = flt(value)
                else:
                    value = value or ""
                row_data[fieldname] = value
            snapshot.append(row_data)
        return snapshot

    def get_valid_transitions(self):
        """Return the list of valid next states from the current status."""
        if self.entry_type == "Purchase":
            return PURCHASE_TRANSITIONS.get(self.status, [])
        elif self.entry_type == "Sales":
            return SALES_TRANSITIONS.get(self.status, [])
        return []

    @frappe.whitelist()
    def change_status(self, new_status, comment=None):
        """
        Transition to a new status with validation and audit logging.

        Args:
            new_status (str): The target status.
            comment (str, optional): Comment for the transition (required for some states).

        Returns:
            str: The new status.
        """
        old_status = self.status

        # Validate transition is allowed
        valid = self.get_valid_transitions()
        if new_status not in valid:
            frappe.throw(
                _("Cannot transition from '{0}' to '{1}'. Valid transitions: {2}").format(
                    old_status, new_status, ", ".join(valid) if valid else "none (terminal state)"
                ),
                title=_("Invalid Status Transition"),
            )

        # Validate comment requirement
        if new_status in COMMENT_REQUIRED_STATES and not comment:
            frappe.throw(
                _("A comment is required when transitioning to '{0}'").format(new_status)
            )

        # Append status log entry
        self.append("status_log", {
            "from_status": old_status,
            "to_status": new_status,
            "changed_by": frappe.session.user,
            "changed_at": now_datetime(),
            "comment": comment or "",
        })

        # Update status and tracking fields
        self.status = new_status
        self.current_status_since = now_datetime()

        self.save()

        frappe.msgprint(
            _("Status changed from {0} to {1}").format(old_status, new_status),
            alert=True,
        )

        return self.status

    def calculate_charge_totals(self):
        """Calculate total from charge details table and sync to amount."""
        total = 0
        for row in self.get("charge_details", []):
            qty = flt(row.qty) or 1
            rate = flt(row.rate)
            row.line_amount = flt(qty * rate, 2)
            total += row.line_amount

        if self.get("charge_details"):
            self.total_charge_amount = flt(total, 2)
            self.amount = flt(total, 2)

    @frappe.whitelist()
    def copy_charges_to_forwarding_working_cost(self):
        """Copy purchase register charges to the linked Forwarding Job working cost table."""
        if self.is_new():
            frappe.throw(_("Please save the Invoice Register Entry before copying charges."))

        self = frappe.get_doc("Invoice Register Entry", self.name)

        if self.entry_type != "Purchase":
            frappe.throw(_("Only Purchase register entries can be copied to Working Cost."))

        if self.job_doctype != "Forwarding Job" or not self.job_name:
            frappe.throw(_("Please link this entry to a Forwarding Job first."))

        if self.status not in ("Ready for Capture", "Returned for Capture"):
            frappe.throw(
                _("Charges can only be copied when status is Ready for Capture or Returned for Capture.")
            )

        if not self.get("charge_details"):
            frappe.throw(_("No charge rows found to copy."))

        job = frappe.get_doc("Forwarding Job", self.job_name)
        job.check_permission("write")

        copied_references = {
            row.source_reference
            for row in job.get("forwarding_cost_charges", [])
            if row.source_reference
        }

        added = 0
        skipped = 0
        missing_supplier = 0

        for charge_row in self.get("charge_details", []):
            if not charge_row.charge:
                continue

            if charge_row.name in copied_references:
                skipped += 1
                continue

            supplier = None
            if charge_row.line_party_type == "Supplier" and charge_row.line_party:
                supplier = charge_row.line_party
            supplier = supplier or self.party

            if not supplier:
                missing_supplier += 1
                continue

            qty = flt(charge_row.qty) or 1.0
            buy_rate = flt(charge_row.rate)
            cost_amount = flt(qty * buy_rate, 2)

            job.append(
                "forwarding_cost_charges",
                {
                    "charge": charge_row.charge,
                    "description": charge_row.description,
                    "qty": qty,
                    "buy_rate": buy_rate,
                    "supplier": supplier,
                    "attachment": charge_row.attachment,
                    "cost_amount": cost_amount,
                    "supplier_invoice_no": self.supplier_invoice_no,
                    "supplier_invoice_date": self.supplier_invoice_date,
                    "source_reference": charge_row.name,
                },
            )

            copied_references.add(charge_row.name)
            added += 1

        if not added:
            if skipped:
                frappe.throw(_("All eligible charge rows have already been copied to the Forwarding Job."))
            if missing_supplier:
                frappe.throw(_("No charges were copied because a supplier is required."))
            frappe.throw(_("No eligible charge rows found to copy."))

        job.save()

        message = _("{0} charge row(s) copied to Forwarding Job {1}.").format(added, job.name)
        if skipped:
            message += " " + _("{0} duplicate row(s) skipped.").format(skipped)
        if missing_supplier:
            message += " " + _("{0} row(s) skipped because supplier was missing.").format(missing_supplier)

        frappe.msgprint(message, alert=True)
        return {
            "added": added,
            "skipped": skipped,
            "missing_supplier": missing_supplier,
            "job_name": job.name,
        }


@frappe.whitelist()
def job_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query for the Job link field that searches by:
    - Job name (e.g. FWJB-00001-26)
    - Customer reference / BL number
    - Customer name

    This allows bookkeepers to find a Forwarding Job by typing
    a BL number (which suppliers reference on their invoices).
    """
    job_doctype = filters.get("job_doctype", "Forwarding Job")

    # Sanitize input
    txt = txt or ""
    search_txt = f"%{txt}%"

    return frappe.db.sql(
        """
        SELECT
            name,
            CONCAT_WS(' | ',
                customer_reference,
                customer,
                bl_number
            ) as description
        FROM `tab{doctype}`
        WHERE
            docstatus < 2
            AND (
                name LIKE %(txt)s
                OR customer_reference LIKE %(txt)s
                OR bl_number LIKE %(txt)s
                OR customer LIKE %(txt)s
            )
        ORDER BY
            CASE
                WHEN name LIKE %(txt)s THEN 0
                WHEN customer_reference LIKE %(txt)s THEN 1
                WHEN bl_number LIKE %(txt)s THEN 2
                ELSE 3
            END,
            modified DESC
        LIMIT %(page_len)s OFFSET %(start)s
    """.format(
            doctype=job_doctype
        ),
        {
            "txt": search_txt,
            "start": start,
            "page_len": page_len,
        },
    )
