# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

from freightmas.portal.print_formats import SETTINGS_FIELD_BY_DOCTYPE, validate_portal_print_format


class FreightMasSettings(Document):
	def validate(self):
		"""
		P1 FIX #4: Validate revenue recognition settings on save.
		Prevents accounts being disabled after configuration.
		"""
		if not self.enable_revenue_recognition:
			pass
		else:
			from freightmas.utils.revenue_recognition import get_recognition_settings
			try:
				get_recognition_settings()
			except Exception as e:
				frappe.throw(
					_("Revenue Recognition is enabled but settings are invalid: {0}. "
					  "Please check that all configured accounts are active ledger accounts.").format(
						str(e)
					)
				)

		if self.tracking_provider == "Traqo" and self.enable_shipping_tracker:
			self.traqo_webhook_url = get_traqo_webhook_url()

		for doctype, fieldname in SETTINGS_FIELD_BY_DOCTYPE.items():
			print_format = self.get(fieldname)
			if print_format:
				validate_portal_print_format(doctype, print_format)


def get_traqo_webhook_url():
	return frappe.utils.get_url(
		"/api/method/freightmas.integrations.tracking.webhook.receive"
	)


@frappe.whitelist()
def get_traqo_webhook_url_api():
	return get_traqo_webhook_url()

