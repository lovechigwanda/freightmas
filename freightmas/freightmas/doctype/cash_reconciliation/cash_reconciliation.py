# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, nowtime


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

	def set_ledger_balance(self):
		if self.ledger_balance is None or not self.fetched_on:
			self.ledger_balance = get_cash_ledger_balance(self.company, self.cash_account, self.posting_date)
			self.fetched_on = now()

	def calculate_difference(self):
		self.difference = flt(self.physical_cash_balance) - flt(self.ledger_balance)

	def set_reconciliation_status(self):
		self.reconciliation_status = "Balanced" if flt(self.difference, 2) == 0 else "Difference"

	def validate_difference_remarks(self, for_submit=False):
		if for_submit and flt(self.difference, 2) != 0 and not self.remarks:
			frappe.throw(_("Remarks are required before submitting a reconciliation with a cash difference."))


@frappe.whitelist()
def get_cash_ledger_balance(company, cash_account, posting_date):
	if not company:
		frappe.throw(_("Company is required."))
	if not cash_account:
		frappe.throw(_("Cash Account is required."))
	if not posting_date:
		frappe.throw(_("Posting Date is required."))

	account = frappe.get_cached_doc("Account", cash_account)
	if account.company != company:
		frappe.throw(_("Cash Account must belong to the selected Company."))
	if account.account_type != "Cash" or account.is_group:
		frappe.throw(_("Please select a non-group Cash Account."))

	balance = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(debit - credit), 0)
		FROM `tabGL Entry`
		WHERE company = %(company)s
			AND account = %(cash_account)s
			AND posting_date <= %(posting_date)s
			AND is_cancelled = 0
		""",
		{
			"company": company,
			"cash_account": cash_account,
			"posting_date": posting_date,
		},
	)[0][0]

	return flt(balance, 2)
