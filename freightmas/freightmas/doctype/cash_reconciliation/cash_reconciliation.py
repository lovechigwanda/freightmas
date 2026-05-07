# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, nowtime, getdate, add_days, get_first_day, get_last_day
from freightmas.freightmas.report.cash_reconciliation_common import get_cash_ledger_balance as _get_cash_ledger_balance


class CashReconciliation(Document):
	def validate(self):
		self.set_defaults()
		self.validate_cash_account()
		self.validate_unique_reconciliation()
		self.set_ledger_balance()
		self.calculate_difference()
		self.set_reconciliation_status()
		self.validate_difference_remarks()
		self.calculate_period_flow()

	def before_submit(self):
		self.calculate_difference()
		self.set_reconciliation_status()
		self.validate_difference_remarks(for_submit=True)
		self.approved_by = frappe.session.user
		self.approved_on = now()
		self.calculate_period_flow()

	def set_defaults(self):
		if not self.posting_time:
			self.posting_time = nowtime()

		if self.company and not self.company_currency:
			self.company_currency = frappe.get_cached_value("Company", self.company, "default_currency")

	def validate_unique_reconciliation(self):
		existing = frappe.db.get_value(
			"Cash Reconciliation",
			{
				"company": self.company,
				"cash_account": self.cash_account,
				"posting_date": self.posting_date,
				"name": ("!=", self.name),
				"docstatus": ("!=", 2),
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("A Cash Reconciliation for {0} on {1} already exists: {2}.").format(
					frappe.bold(self.cash_account), frappe.bold(self.posting_date), frappe.bold(existing)
				)
			)

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

	def calculate_period_flow(self):
		if not (self.company and self.cash_account and self.posting_date):
			return
		period_type = self.period_type or "Day"
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		period_from, period_to = _get_period_dates(self.posting_date, period_type)

		row = frappe.db.sql(
			"""
			SELECT
				COALESCE(SUM(debit_in_account_currency), 0),
				COALESCE(SUM(credit_in_account_currency), 0)
			FROM `tabGL Entry`
			WHERE company = %(company)s
				AND account = %(cash_account)s
				AND posting_date >= %(period_from)s
				AND posting_date <= %(period_to)s
				AND is_cancelled = 0
				AND (account_currency IS NULL OR account_currency = %(currency)s)
			""",
			{
				"company": self.company,
				"cash_account": self.cash_account,
				"period_from": period_from,
				"period_to": period_to,
				"currency": company_currency,
			},
		)[0]

		self.period_from = period_from
		self.period_to = period_to
		self.period_receipts = flt(row[0], 2)
		self.period_payments = flt(row[1], 2)
		self.period_net_flow = flt(self.period_receipts - self.period_payments, 2)


def _get_period_dates(posting_date, period_type):
	d = getdate(posting_date)
	if period_type == "Week":
		start = add_days(d, -d.weekday())
		return getdate(start), getdate(add_days(start, 6))
	elif period_type == "Month":
		return getdate(get_first_day(d)), getdate(get_last_day(d))
	return d, d


@frappe.whitelist()
@frappe.whitelist()
def get_cash_ledger_balance(company, cash_account, posting_date):
	"""API endpoint wrapper for fetching cash ledger balance."""
	frappe.has_permission("Cash Reconciliation", "read", None, throw=True)
	return _get_cash_ledger_balance(company, cash_account, posting_date)


@frappe.whitelist()
def get_period_flow(company, cash_account, posting_date, period_type="Day"):
	frappe.has_permission("Cash Reconciliation", "read", None, throw=True)
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	period_from, period_to = _get_period_dates(posting_date, period_type)

	row = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(debit_in_account_currency), 0),
			COALESCE(SUM(credit_in_account_currency), 0)
		FROM `tabGL Entry`
		WHERE company = %(company)s
			AND account = %(cash_account)s
			AND posting_date >= %(period_from)s
			AND posting_date <= %(period_to)s
			AND is_cancelled = 0
			AND (account_currency IS NULL OR account_currency = %(currency)s)
		""",
		{
			"company": company,
			"cash_account": cash_account,
			"period_from": period_from,
			"period_to": period_to,
			"currency": company_currency,
		},
	)[0]

	receipts = flt(row[0], 2)
	payments = flt(row[1], 2)
	return {
		"period_from": str(period_from),
		"period_to": str(period_to),
		"period_receipts": receipts,
		"period_payments": payments,
		"period_net_flow": flt(receipts - payments, 2),
	}
