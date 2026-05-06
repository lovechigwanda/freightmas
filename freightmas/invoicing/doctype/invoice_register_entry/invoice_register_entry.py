# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, get_datetime, add_to_date
from frappe import _
from datetime import timedelta


# ========================================================
# JOB DOCTYPE ALLOWLIST — prevents SQL injection in job_query
# ========================================================
VALID_JOB_DOCTYPES = frozenset({"Forwarding Job"})


# ========================================================
# VALID TRANSITIONS PER ENTRY TYPE
# ========================================================

PURCHASE_TRANSITIONS = {
    "Received": ["Submitted for Approval", "Cancelled"],
    # Issue 11 fix: direct approval path added alongside correction path
    "Submitted for Approval": ["Ready for Capture", "Returned for Capture", "Query with Supplier"],
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

# States that require a comment
COMMENT_REQUIRED_STATES = {"Query with Supplier", "Returned to Draft", "Cancelled"}

# Terminal states — no further transitions allowed
TERMINAL_STATES = {"Captured", "Issued to Client", "Cancelled"}

LOCKED_STATUSES = {"Captured", "Issued to Client"}

# Fields frozen once the entry is captured or linked to an invoice.
# total_charge_amount is intentionally excluded — it is always derived
# from charge_details rows, which are independently checked below.
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
}

NUMERIC_CHILD_FIELDS = {"qty", "rate", "line_amount"}


# ========================================================
# WORKING DAYS UTILITY
# ========================================================

def _count_working_days(start_dt, end_dt):
    """Count weekday (Mon–Fri) days between two datetimes."""
    if not start_dt or not end_dt:
        return 0.0
    start = get_datetime(start_dt).date()
    end = get_datetime(end_dt).date()
    if end <= start:
        return 0.0
    days = 0
    current = start
    while current < end:
        if current.weekday() < 5:  # 0=Mon … 4=Fri
            days += 1
        current += timedelta(days=1)
    return float(days)


# ========================================================
# DOCUMENT CLASS
# ========================================================

class InvoiceRegisterEntry(Document):

    def validate(self):
        self.set_party_type_from_entry_type()
        self.calculate_charge_totals()
        self.compute_base_amount()
        self.validate_job_reference()
        self.compute_is_overdue()
        self.notify_instruction_on_invoice_link()
        self.validate_locked_entry()

    def on_trash(self):
        if self.is_locked():
            frappe.throw(self.get_locked_message(), title=_("Invoice Register Entry Locked"))

    def before_insert(self):
        if not self.status:
            if self.entry_type == "Purchase":
                self.status = "Received"
            elif self.entry_type == "Sales":
                self.status = "Instruction Received"

        if not self.received_on:
            self.received_on = now_datetime()

        self.current_status_since = now_datetime()
        self.compute_sla_due_at()

    # ----------------------------------------------------------
    # FIELD HELPERS
    # ----------------------------------------------------------

    def set_party_type_from_entry_type(self):
        if self.entry_type == "Sales" and self.party_type != "Customer":
            self.party_type = "Customer"
        elif self.entry_type == "Purchase" and self.party_type != "Supplier":
            self.party_type = "Supplier"

    def compute_base_amount(self):
        rate = flt(self.conversion_rate) or 1.0
        self.amount_base = flt(flt(self.amount) * rate, 2)

    def validate_job_reference(self):
        if self.job_doctype and self.job_name:
            if not frappe.db.exists(self.job_doctype, self.job_name):
                frappe.throw(
                    _("{0} {1} does not exist").format(self.job_doctype, self.job_name)
                )
            if not self.company:
                self.company = frappe.db.get_value(
                    self.job_doctype, self.job_name, "company"
                )

    def calculate_charge_totals(self):
        """
        Recompute line_amount on every charge row and sync total_charge_amount.

        amount is synced from the charge table when rows exist so the two fields
        stay consistent. When there are no charge rows, amount can be set manually
        and total_charge_amount reflects 0 (no line-item breakdown).
        """
        total = 0.0
        for row in self.get("charge_details", []):
            qty = flt(row.qty) or 1
            rate = flt(row.rate)
            row.line_amount = flt(qty * rate, 2)
            total += row.line_amount

        self.total_charge_amount = flt(total, 2)
        if self.get("charge_details"):
            self.amount = self.total_charge_amount

    # ----------------------------------------------------------
    # SLA / OVERDUE
    # ----------------------------------------------------------

    def compute_sla_due_at(self):
        """Set sla_due_at from FreightMas Settings for the current status."""
        if self.status in TERMINAL_STATES:
            self.sla_due_at = None
            return

        hours = self._get_sla_hours_for_status(self.status)
        if not hours or not self.current_status_since:
            return

        self.sla_due_at = add_to_date(
            get_datetime(self.current_status_since), hours=hours
        )

    def _get_sla_hours_for_status(self, status):
        """Return the SLA window in hours for a given status from FreightMas Settings."""
        try:
            settings = frappe.get_single("FreightMas Settings")
        except Exception:
            return None

        sla_map = {
            "Received": flt(settings.sla_supplier_invoice_routing_hours) or 24,
            "Submitted for Approval": flt(settings.sla_supplier_approval_hours) or 24,
            "Query with Supplier": (flt(settings.sla_query_resolution_days) or 2) * 24,
            "Instruction Received": flt(settings.sla_sales_invoice_turnaround_hours) or 3,
        }
        return sla_map.get(status)

    def compute_is_overdue(self):
        """Set is_overdue = 1 when past the SLA window and not in a terminal state."""
        if self.status in TERMINAL_STATES or not self.sla_due_at:
            self.is_overdue = 0
            return
        self.is_overdue = 1 if now_datetime() > get_datetime(self.sla_due_at) else 0

    # ----------------------------------------------------------
    # INSTRUCTION LIFECYCLE
    # ----------------------------------------------------------

    def notify_instruction_on_invoice_link(self):
        """
        When a Sales Invoice is newly linked to a Sales register entry,
        mark the originating Invoicing Instruction as Actioned.
        """
        if (
            self.entry_type != "Sales"
            or not self.linked_sales_invoice
            or not self.linked_invoicing_instruction
        ):
            return

        original = self.get_doc_before_save()
        if original and original.linked_sales_invoice == self.linked_sales_invoice:
            return  # no change — don't re-trigger

        instruction = frappe.get_doc("Invoicing Instruction", self.linked_invoicing_instruction)
        if instruction.status not in ("Actioned", "Cancelled"):
            instruction.mark_as_actioned(self.linked_sales_invoice)

    # ----------------------------------------------------------
    # LOCKING
    # ----------------------------------------------------------

    def is_locked(self):
        return (
            self.status in LOCKED_STATUSES
            or bool(self.linked_purchase_invoice)
            or bool(self.linked_sales_invoice)
        )

    def get_locked_message(self):
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
        Block edits to business fields once the entry is captured or invoice-linked.

        The transition *into* a locked state is always permitted; only subsequent
        edits after the lock is established are rejected.
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
        current_value = self.get(fieldname)
        original_value = original.get(fieldname)
        if fieldname in NUMERIC_LOCKED_FIELDS:
            return flt(current_value) != flt(original_value)
        return (current_value or "") != (original_value or "")

    def has_charge_details_changed(self, original):
        return self.get_locked_charge_snapshot(self) != self.get_locked_charge_snapshot(original)

    def get_locked_charge_snapshot(self, doc):
        snapshot = []
        for row in doc.get("charge_details", []):
            row_data = {"name": row.name, "idx": row.idx}
            for fieldname in LOCKED_CHILD_FIELDS:
                value = row.get(fieldname)
                if fieldname in NUMERIC_CHILD_FIELDS:
                    value = flt(value)
                else:
                    value = value or ""
                row_data[fieldname] = value
            snapshot.append(row_data)
        return snapshot

    # ----------------------------------------------------------
    # STATUS MACHINE
    # ----------------------------------------------------------

    def get_valid_transitions(self):
        if self.entry_type == "Purchase":
            return PURCHASE_TRANSITIONS.get(self.status, [])
        elif self.entry_type == "Sales":
            return SALES_TRANSITIONS.get(self.status, [])
        return []

    @frappe.whitelist()
    def change_status(self, new_status, comment=None):
        """
        Transition to a new workflow status.

        Validates the transition, records working days spent in the previous
        status, appends an audit log row, resets the SLA window, then saves.
        """
        old_status = self.status

        valid = self.get_valid_transitions()
        if new_status not in valid:
            frappe.throw(
                _("Cannot transition from '{0}' to '{1}'. Valid transitions: {2}").format(
                    old_status,
                    new_status,
                    ", ".join(valid) if valid else _("none (terminal state)"),
                ),
                title=_("Invalid Status Transition"),
            )

        if new_status in COMMENT_REQUIRED_STATES and not comment:
            frappe.throw(
                _("A comment is required when transitioning to '{0}'").format(new_status)
            )

        working_days = _count_working_days(self.current_status_since, now_datetime())

        self.append("status_log", {
            "from_status": old_status,
            "to_status": new_status,
            "changed_by": frappe.session.user,
            "changed_at": now_datetime(),
            "comment": comment or "",
            "working_days_in_previous_status": working_days,
        })

        self.status = new_status
        self.current_status_since = now_datetime()
        self.compute_sla_due_at()

        self.save()

        frappe.msgprint(
            _("Status changed from {0} to {1}").format(old_status, new_status),
            alert=True,
        )

        return self.status

    # ----------------------------------------------------------
    # CHARGE COPY TO FORWARDING JOB
    # ----------------------------------------------------------

    @frappe.whitelist()
    def copy_charges_to_forwarding_working_cost(self):
        """Copy purchase register charges to the linked Forwarding Job working cost table."""
        if self.is_new():
            frappe.throw(_("Please save the Invoice Register Entry before copying charges."))

        # Issue 2 fix: use a named variable instead of reassigning self
        doc = frappe.get_doc("Invoice Register Entry", self.name)

        if doc.entry_type != "Purchase":
            frappe.throw(_("Only Purchase register entries can be copied to Working Cost."))

        if doc.job_doctype != "Forwarding Job" or not doc.job_name:
            frappe.throw(_("Please link this entry to a Forwarding Job first."))

        if doc.status not in ("Ready for Capture", "Returned for Capture"):
            frappe.throw(
                _("Charges can only be copied when status is Ready for Capture or Returned for Capture.")
            )

        if not doc.get("charge_details"):
            frappe.throw(_("No charge rows found to copy."))

        job = frappe.get_doc("Forwarding Job", doc.job_name)
        job.check_permission("write")

        copied_references = {
            row.source_reference
            for row in job.get("forwarding_cost_charges", [])
            if row.source_reference
        }

        added = 0
        skipped = 0
        missing_supplier = 0

        for charge_row in doc.get("charge_details", []):
            if not charge_row.charge:
                continue

            if charge_row.name in copied_references:
                skipped += 1
                continue

            supplier = None
            if charge_row.line_party_type == "Supplier" and charge_row.line_party:
                supplier = charge_row.line_party
            supplier = supplier or doc.party

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
                    "supplier_invoice_no": doc.supplier_invoice_no,
                    "supplier_invoice_date": doc.supplier_invoice_date,
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


# ========================================================
# WHITELISTED API
# ========================================================

@frappe.whitelist()
def job_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom link-field query that searches Forwarding Jobs by name,
    customer reference, BL number, or customer name.

    Used by bookkeepers who receive supplier invoices quoting a BL number.
    """
    job_doctype = filters.get("job_doctype", "Forwarding Job")

    # Issue 1 fix: validate against an allowlist before interpolating into SQL
    if job_doctype not in VALID_JOB_DOCTYPES:
        frappe.throw(_("Invalid job type: {0}").format(frappe.bold(job_doctype)))

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
        """.format(doctype=job_doctype),
        {
            "txt": search_txt,
            "start": start,
            "page_len": page_len,
        },
    )


# ========================================================
# SCHEDULED TASK
# ========================================================

def update_overdue_entries():
    """
    Daily task: sync is_overdue on all non-terminal Invoice Register Entries.

    Marking happens in bulk via db_set to avoid triggering validate hooks on
    every entry. update_modified=False keeps the audit trail clean.
    """
    now = now_datetime()

    entries_to_flag = frappe.db.get_all(
        "Invoice Register Entry",
        filters={
            "status": ["not in", list(TERMINAL_STATES)],
            "sla_due_at": ["<", now],
            "is_overdue": 0,
        },
        pluck="name",
    )
    for name in entries_to_flag:
        frappe.db.set_value(
            "Invoice Register Entry", name, "is_overdue", 1, update_modified=False
        )

    entries_to_clear = frappe.db.get_all(
        "Invoice Register Entry",
        filters={
            "status": ["in", list(TERMINAL_STATES)],
            "is_overdue": 1,
        },
        pluck="name",
    )
    for name in entries_to_clear:
        frappe.db.set_value(
            "Invoice Register Entry", name, "is_overdue", 0, update_modified=False
        )

    if entries_to_flag or entries_to_clear:
        frappe.db.commit()
