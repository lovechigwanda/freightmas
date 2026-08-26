# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Tests for FreightMas Email Template rendering."""

import frappe
from frappe.tests import IntegrationTestCase

from freightmas.notifications.email_context import render_template_by_name
from freightmas.notifications.email_templates import TEMPLATE_REGISTRY


class TestEmailTemplates(IntegrationTestCase):
	def test_registry_has_all_templates(self):
		self.assertEqual(len(TEMPLATE_REGISTRY), 5)

	def test_status_update_template_renders(self):
		if not frappe.db.exists("Email Template", "Shipment Status Update"):
			self.skipTest("Shipment Status Update template not seeded")
		context = {
			"name": "FWD-TEST-001",
			"customer_name": "Test Customer",
			"company_name": "Test Co",
			"company": frappe.defaults.get_global_default("company"),
			"status_label": "Customs release obtained",
			"status_datetime": "14 Aug 2026 09:30",
			"next_step": "Delivery to consignee",
			"email_date": "14 Aug 2026",
		}
		rendered = render_template_by_name("Shipment Status Update", context, company=context.get("company"))
		self.assertIn("TRACKING UPDATE", rendered["message"])
		self.assertIn("Customs release obtained", rendered["message"])
		self.assertIn("data-fm-email", rendered["message"])

	def test_documentation_request_template_renders(self):
		if not frappe.db.exists("Email Template", "Documentation Request"):
			self.skipTest("Documentation Request template not seeded")
		context = {
			"name": "FWD-TEST-001",
			"customer_name": "Test Customer",
			"company_name": "Test Co",
			"company": frappe.defaults.get_global_default("company"),
			"bl_number_display": "BL123",
			"missing_docs": ["Commercial Invoice", "Packing List"],
			"email_date": "14 Aug 2026",
		}
		rendered = render_template_by_name("Documentation Request", context, company=context.get("company"))
		self.assertIn("DOCUMENTATION REQUEST", rendered["message"])
		self.assertIn("Commercial Invoice", rendered["message"])
