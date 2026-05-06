# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime, now_datetime

from freightmas.invoicing.doctype.invoice_register_entry.invoice_register_entry import (
    _count_working_days,
    PURCHASE_TRANSITIONS,
    SALES_TRANSITIONS,
    TERMINAL_STATES,
    LOCKED_STATUSES,
)


def _make_entry(entry_type="Purchase", status=None):
    """Return an in-memory Invoice Register Entry for logic testing (not inserted)."""
    doc = frappe.get_doc({
        "doctype": "Invoice Register Entry",
        "entry_type": entry_type,
        "party_type": "Supplier" if entry_type == "Purchase" else "Customer",
    })
    if status:
        doc.status = status
    return doc


class TestInvoiceRegisterEntry(FrappeTestCase):

    # ----------------------------------------------------------
    # State machine — transitions
    # ----------------------------------------------------------

    def test_purchase_transitions_from_received(self):
        doc = _make_entry("Purchase", "Received")
        transitions = doc.get_valid_transitions()
        self.assertIn("Submitted for Approval", transitions)
        self.assertIn("Cancelled", transitions)

    def test_purchase_approval_has_direct_ready_for_capture_path(self):
        """Issue 11 fix: approver can go straight to Ready for Capture."""
        doc = _make_entry("Purchase", "Submitted for Approval")
        self.assertIn("Ready for Capture", doc.get_valid_transitions())

    def test_purchase_approval_can_also_return_for_corrections(self):
        doc = _make_entry("Purchase", "Submitted for Approval")
        self.assertIn("Returned for Capture", doc.get_valid_transitions())

    def test_purchase_approval_can_query_supplier(self):
        doc = _make_entry("Purchase", "Submitted for Approval")
        self.assertIn("Query with Supplier", doc.get_valid_transitions())

    def test_terminal_states_have_no_transitions(self):
        for status in TERMINAL_STATES:
            doc = _make_entry("Purchase", status)
            self.assertEqual(
                doc.get_valid_transitions(), [],
                msg=f"Expected no transitions from terminal state '{status}'"
            )

    def test_sales_transitions_from_instruction_received(self):
        doc = _make_entry("Sales", "Instruction Received")
        transitions = doc.get_valid_transitions()
        self.assertIn("Drafted", transitions)
        self.assertIn("Cancelled", transitions)

    def test_sales_returned_to_draft_can_re_draft(self):
        doc = _make_entry("Sales", "Returned to Draft")
        self.assertIn("Drafted", doc.get_valid_transitions())

    def test_invalid_entry_type_returns_empty_transitions(self):
        doc = _make_entry("Purchase", "Received")
        doc.entry_type = "Unknown"
        self.assertEqual(doc.get_valid_transitions(), [])

    def test_all_purchase_statuses_have_defined_transitions(self):
        for status in PURCHASE_TRANSITIONS:
            doc = _make_entry("Purchase", status)
            # Should not raise — even terminal states return []
            doc.get_valid_transitions()

    def test_all_sales_statuses_have_defined_transitions(self):
        for status in SALES_TRANSITIONS:
            doc = _make_entry("Sales", status)
            doc.get_valid_transitions()

    # ----------------------------------------------------------
    # Locking
    # ----------------------------------------------------------

    def test_locked_when_status_is_captured(self):
        doc = _make_entry("Purchase", "Captured")
        self.assertTrue(doc.is_locked())

    def test_locked_when_status_is_issued_to_client(self):
        doc = _make_entry("Sales", "Issued to Client")
        self.assertTrue(doc.is_locked())

    def test_locked_when_purchase_invoice_present(self):
        doc = _make_entry("Purchase", "Received")
        doc.linked_purchase_invoice = "PINV-00001"
        self.assertTrue(doc.is_locked())

    def test_locked_when_sales_invoice_present(self):
        doc = _make_entry("Sales", "Instruction Received")
        doc.linked_sales_invoice = "SINV-00001"
        self.assertTrue(doc.is_locked())

    def test_not_locked_in_intermediate_purchase_state(self):
        for status in ("Received", "Submitted for Approval", "Ready for Capture", "Returned for Capture", "Query with Supplier"):
            doc = _make_entry("Purchase", status)
            self.assertFalse(doc.is_locked(), msg=f"Should not be locked in '{status}'")

    def test_not_locked_in_intermediate_sales_state(self):
        for status in ("Instruction Received", "Drafted", "Returned to Draft"):
            doc = _make_entry("Sales", status)
            self.assertFalse(doc.is_locked(), msg=f"Should not be locked in '{status}'")

    # ----------------------------------------------------------
    # Charge totals
    # ----------------------------------------------------------

    def test_charge_totals_computed_from_rows(self):
        doc = _make_entry("Purchase", "Received")
        doc.append("charge_details", {"charge": "ITEM-001", "qty": 2, "rate": 100.0})
        doc.append("charge_details", {"charge": "ITEM-002", "qty": 1, "rate": 50.0})
        doc.calculate_charge_totals()
        self.assertEqual(doc.total_charge_amount, 250.0)
        self.assertEqual(doc.amount, 250.0)

    def test_charge_totals_defaults_qty_to_one(self):
        doc = _make_entry("Purchase", "Received")
        doc.append("charge_details", {"charge": "ITEM-001", "qty": 0, "rate": 200.0})
        doc.calculate_charge_totals()
        self.assertEqual(doc.total_charge_amount, 200.0)

    def test_charge_totals_without_rows_does_not_override_manual_amount(self):
        """When no charge rows exist, manually entered amount must be preserved."""
        doc = _make_entry("Purchase", "Received")
        doc.amount = 999.0
        doc.calculate_charge_totals()
        self.assertEqual(doc.total_charge_amount, 0.0)
        self.assertEqual(doc.amount, 999.0)

    def test_charge_totals_always_sets_total_charge_amount_to_zero_when_empty(self):
        doc = _make_entry("Purchase", "Received")
        doc.total_charge_amount = 500.0  # stale value
        doc.calculate_charge_totals()
        self.assertEqual(doc.total_charge_amount, 0.0)

    # ----------------------------------------------------------
    # Working days counter
    # ----------------------------------------------------------

    def test_count_working_days_mon_to_fri(self):
        # Monday 2026-05-04 → Friday 2026-05-08 = 4 working days
        start = get_datetime("2026-05-04 09:00:00")
        end = get_datetime("2026-05-08 09:00:00")
        self.assertEqual(_count_working_days(start, end), 4.0)

    def test_count_working_days_spans_weekend(self):
        # Friday 2026-05-08 → Monday 2026-05-11 = 1 working day (just Fri)
        start = get_datetime("2026-05-08 09:00:00")
        end = get_datetime("2026-05-11 09:00:00")
        self.assertEqual(_count_working_days(start, end), 1.0)

    def test_count_working_days_same_day_returns_zero(self):
        dt = get_datetime("2026-05-06 10:00:00")
        self.assertEqual(_count_working_days(dt, dt), 0.0)

    def test_count_working_days_end_before_start_returns_zero(self):
        start = get_datetime("2026-05-08 09:00:00")
        end = get_datetime("2026-05-04 09:00:00")
        self.assertEqual(_count_working_days(start, end), 0.0)

    def test_count_working_days_none_inputs_return_zero(self):
        self.assertEqual(_count_working_days(None, now_datetime()), 0.0)
        self.assertEqual(_count_working_days(now_datetime(), None), 0.0)

    # ----------------------------------------------------------
    # SLA / overdue
    # ----------------------------------------------------------

    def test_compute_is_overdue_returns_zero_for_terminal_state(self):
        doc = _make_entry("Purchase", "Captured")
        doc.sla_due_at = "2020-01-01 00:00:00"  # well past
        doc.compute_is_overdue()
        self.assertEqual(doc.is_overdue, 0)

    def test_compute_is_overdue_returns_zero_when_no_sla(self):
        doc = _make_entry("Purchase", "Received")
        doc.sla_due_at = None
        doc.compute_is_overdue()
        self.assertEqual(doc.is_overdue, 0)

    def test_compute_is_overdue_returns_one_when_past_sla(self):
        doc = _make_entry("Purchase", "Received")
        doc.sla_due_at = "2020-01-01 00:00:00"
        doc.compute_is_overdue()
        self.assertEqual(doc.is_overdue, 1)

    def test_compute_is_overdue_returns_zero_when_future_sla(self):
        doc = _make_entry("Purchase", "Received")
        doc.sla_due_at = "2099-12-31 23:59:59"
        doc.compute_is_overdue()
        self.assertEqual(doc.is_overdue, 0)

    # ----------------------------------------------------------
    # Field helpers
    # ----------------------------------------------------------

    def test_set_party_type_sales(self):
        doc = _make_entry("Sales")
        doc.party_type = ""
        doc.set_party_type_from_entry_type()
        self.assertEqual(doc.party_type, "Customer")

    def test_set_party_type_purchase(self):
        doc = _make_entry("Purchase")
        doc.party_type = ""
        doc.set_party_type_from_entry_type()
        self.assertEqual(doc.party_type, "Supplier")

    def test_compute_base_amount(self):
        doc = _make_entry("Purchase")
        doc.amount = 1000.0
        doc.conversion_rate = 2.5
        doc.compute_base_amount()
        self.assertEqual(doc.amount_base, 2500.0)

    def test_compute_base_amount_defaults_rate_to_one(self):
        doc = _make_entry("Purchase")
        doc.amount = 500.0
        doc.conversion_rate = 0  # should default to 1
        doc.compute_base_amount()
        self.assertEqual(doc.amount_base, 500.0)

    # ----------------------------------------------------------
    # Locked message
    # ----------------------------------------------------------

    def test_locked_message_when_purchase_invoice_linked(self):
        doc = _make_entry("Purchase", "Captured")
        doc.name = "IVREG-00001"
        doc.linked_purchase_invoice = "PINV-00001"
        msg = doc.get_locked_message()
        self.assertIn("Purchase Invoice", msg)
        self.assertIn("PINV-00001", msg)

    def test_locked_message_when_status_locked(self):
        doc = _make_entry("Purchase", "Captured")
        doc.name = "IVREG-00001"
        doc.linked_purchase_invoice = None
        doc.linked_sales_invoice = None
        msg = doc.get_locked_message()
        self.assertIn("Captured", msg)
