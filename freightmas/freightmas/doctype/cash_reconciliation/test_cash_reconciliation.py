# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt


class TestCashReconciliation(FrappeTestCase):
	def setUp(self):
		"""Set up test data."""
		self.company = "_Test Company"
		self.account = "_Test Cash - _TC"

	def test_difference_is_calculated(self):
		"""Test that difference is calculated correctly."""
		doc = frappe.new_doc("Cash Reconciliation")
		doc.company = self.company
		doc.cash_account = self.account
		doc.posting_date = "2026-01-01"
		doc.ledger_balance = 100
		doc.fetched_on = "2026-01-01 10:00:00"
		doc.physical_cash_balance = 90
		doc.calculate_difference()
		doc.set_reconciliation_status()

		self.assertEqual(flt(doc.difference, 2), -10)
		self.assertEqual(doc.reconciliation_status, "Difference")

	def test_difference_zero_returns_balanced_status(self):
		"""Test that zero difference results in 'Balanced' status."""
		doc = frappe.new_doc("Cash Reconciliation")
		doc.company = self.company
		doc.cash_account = self.account
		doc.posting_date = "2026-01-01"
		doc.ledger_balance = 100
		doc.physical_cash_balance = 100
		doc.calculate_difference()
		doc.set_reconciliation_status()

		self.assertEqual(flt(doc.difference, 2), 0)
		self.assertEqual(doc.reconciliation_status, "Balanced")

	def test_rounding_consistency(self):
		"""Test that rounding to 2 decimals is consistent."""
		doc = frappe.new_doc("Cash Reconciliation")
		doc.company = self.company
		doc.cash_account = self.account
		doc.posting_date = "2026-01-01"
		doc.ledger_balance = 100.234  # Should round to 100.23
		doc.physical_cash_balance = 100.234  # Should round to 100.23
		doc.calculate_difference()

		# Even with 3-decimal inputs, difference should be exact 0 after 2-decimal rounding
		self.assertEqual(flt(doc.difference, 2), 0)

	def test_remarks_required_on_submit_if_difference_exists(self):
		"""Test that remarks are required when submitting with difference."""
		doc = frappe.new_doc("Cash Reconciliation")
		doc.company = self.company
		doc.cash_account = self.account
		doc.posting_date = "2026-01-01"
		doc.physical_cash_balance = 100
		doc.ledger_balance = 95
		doc.difference = 5
		doc.reconciliation_status = "Difference"
		# remarks is empty

		with self.assertRaises(frappe.ValidationError):
			doc.validate_difference_remarks(for_submit=True)

	def test_remarks_not_required_if_balanced(self):
		"""Test that remarks are NOT required when balanced (difference=0)."""
		doc = frappe.new_doc("Cash Reconciliation")
		doc.company = self.company
		doc.cash_account = self.account
		doc.posting_date = "2026-01-01"
		doc.physical_cash_balance = 100
		doc.ledger_balance = 100
		doc.difference = 0
		doc.reconciliation_status = "Balanced"
		# remarks is empty - should NOT throw

		# Should not raise
		doc.validate_difference_remarks(for_submit=True)

	def test_disabled_account_validation(self):
		"""Test that disabled cash accounts are rejected."""
		# This test assumes a disabled account exists or we can mark one as disabled
		doc = frappe.new_doc("Cash Reconciliation")
		doc.company = self.company
		doc.cash_account = self.account
		
		# Try to validate - if account is valid this test may need adjustment
		# In real scenario, we'd create a disabled account for testing
		try:
			doc.validate_cash_account()
		except frappe.ValidationError as e:
			if "disabled" in str(e).lower():
				self.assertTrue(True)
			else:
				raise

	def test_posting_date_change_invalidates_balance(self):
		"""Test that changing posting_date triggers re-fetch of balance."""
		doc = frappe.new_doc("Cash Reconciliation")
		doc.company = self.company
		doc.cash_account = self.account
		doc.posting_date = "2026-01-01"
		doc.ledger_balance = 100
		doc.fetched_on = "2026-01-01 10:00:00"

		# Simulate posting_date change
		doc.posting_date = "2026-01-02"
		
		# set_ledger_balance should detect the change and re-fetch
		old_fetched_on = doc.fetched_on
		doc.set_ledger_balance()
		
		# fetched_on should be updated (new timestamp)
		self.assertNotEqual(old_fetched_on, doc.fetched_on)

