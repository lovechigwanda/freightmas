# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class WeeklyCashStatementBalance(Document):
	def validate(self):
		self._validate_saturday()
		self._validate_no_duplicate_accounts()
		self._validate_balances_exist()

	def _validate_saturday(self):
		d = getdate(self.week_ending_date)
		# weekday(): Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
		if d.weekday() != 5:
			frappe.throw(_("Week Ending Date must be a Saturday (got {0})").format(
				d.strftime("%A, %d %b %Y")
			))

	def _validate_no_duplicate_accounts(self):
		"""Ensure no account appears more than once in the balances table."""
		if not self.balances:
			return
		
		accounts_seen = set()
		for idx, row in enumerate(self.balances, 1):
			if not row.account:
				continue
			if row.account in accounts_seen:
				frappe.throw(_("Account {0} appears more than once in the balances table (rows {1})").format(
					row.account, idx
				))
			accounts_seen.add(row.account)

	def _validate_balances_exist(self):
		"""Ensure at least one balance entry exists."""
		if not self.balances or len(self.balances) == 0:
			frappe.throw(_("Please add at least one account balance entry."))

