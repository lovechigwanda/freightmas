# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCashReconciliation(FrappeTestCase):
	def test_difference_is_calculated(self):
		doc = frappe.new_doc("Cash Reconciliation")
		doc.company = "_Test Company"
		doc.cash_account = "_Test Cash - _TC"
		doc.posting_date = "2026-01-01"
		doc.ledger_balance = 100
		doc.fetched_on = "2026-01-01 10:00:00"
		doc.physical_cash_balance = 90
		doc.calculate_difference()
		doc.set_reconciliation_status()

		self.assertEqual(doc.difference, -10)
		self.assertEqual(doc.reconciliation_status, "Difference")
