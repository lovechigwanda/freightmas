# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class FreightMasSettings(Document):
	def validate(self):
		"""
		P1 FIX #4: Validate revenue recognition settings on save.
		Prevents accounts being disabled after configuration.
		"""
		if not self.enable_revenue_recognition:
			return
		
		# Validate all configured accounts exist and are enabled
		from freightmas.utils.revenue_recognition import get_recognition_settings
		
		try:
			settings = get_recognition_settings()
			# If this succeeds, all accounts are valid
		except Exception as e:
			frappe.throw(
				_("Revenue Recognition is enabled but settings are invalid: {0}. "
				  "Please check that all configured accounts are active ledger accounts.").format(
					str(e)
				)
			)

