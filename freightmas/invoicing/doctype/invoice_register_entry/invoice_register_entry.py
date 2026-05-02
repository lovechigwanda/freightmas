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


class InvoiceRegisterEntry(Document):

    def validate(self):
        """Validate document before saving."""
        self.set_party_type_from_entry_type()
        self.calculate_charge_totals()
        self.compute_base_amount()
        self.validate_job_reference()

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
