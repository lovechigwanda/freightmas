# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, nowtime
from freightmas.freightmas.report.cash_reconciliation_common import get_cash_ledger_balance as _get_cash_ledger_balance
from freightmas.utils.permissions import check_freightmas_role


class CashReconciliation(Document):
	def validate(self):
		self.set_defaults()
		self.validate_cash_account()
		self.set_ledger_balance()
		self.calculate_difference()
		self.set_reconciliation_status()
		self.validate_difference_remarks()

	def before_submit(self):
		self.calculate_difference()
		self.set_reconciliation_status()
		self.validate_difference_remarks(for_submit=True)
		self.approved_by = frappe.session.user
		self.approved_on = now()

	def set_defaults(self):
		if not self.posting_time:
			self.posting_time = nowtime()

		if self.company and not self.company_currency:
			self.company_currency = frappe.get_cached_value("Company", self.company, "default_currency")

	def validate_cash_account(self):
		if not self.cash_account:
			return

		account = frappe.get_cached_doc("Account", self.cash_account)
		if account.company != self.company:
			frappe.throw(_("Cash Account must belong to company {0}.").format(frappe.bold(self.company)))

		if account.is_group:
			frappe.throw(_("Please select a non-group Cash Account."))

		if account.account_type != "Cash":
			frappe.throw(_("Please select an account with Account Type Cash."))

		if account.disabled:
			frappe.throw(_("Cannot reconcile a disabled Cash Account."))

	def set_ledger_balance(self):
		# Always re-fetch if posting_date changes or balance not yet fetched
		if not self.fetched_on or self.has_value_changed("posting_date"):
			self.ledger_balance = _get_cash_ledger_balance(self.company, self.cash_account, self.posting_date)
			self.fetched_on = now()

	def calculate_difference(self):
		# Calculate and round to 2 decimal places for consistency
		physical = flt(self.physical_cash_balance, 2)
		ledger = flt(self.ledger_balance, 2)
		self.difference = flt(physical - ledger, 2)

	def set_reconciliation_status(self):
		# Determine status based on exact 2-decimal precision
		self.reconciliation_status = "Balanced" if flt(self.difference, 2) == 0 else "Difference"

	def validate_difference_remarks(self, for_submit=False):
		if for_submit and flt(self.difference, 2) != 0 and not self.remarks:
			frappe.throw(_("Remarks are required before submitting a reconciliation with a cash difference."))


@frappe.whitelist()
def get_cash_ledger_balance(company, cash_account, posting_date):
	"""API endpoint wrapper for fetching cash ledger balance.
	
	Requires FreightMas User role. Delegates to common utility function.
	"""
	check_freightmas_role("FreightMas User")
	return _get_cash_ledger_balance(company, cash_account, posting_date)
