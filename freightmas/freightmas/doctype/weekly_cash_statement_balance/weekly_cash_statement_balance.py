# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class WeeklyCashStatementBalance(Document):
	def validate(self):
		self._validate_saturday()

	def _validate_saturday(self):
		d = getdate(self.week_ending_date)
		# weekday(): Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
		if d.weekday() != 5:
			frappe.throw(_("Week Ending Date must be a Saturday (got {0})").format(
				d.strftime("%A, %d %b %Y")
			))
