# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""Tests for client portal print format allowlist and PDF downloads."""

import frappe
from frappe.tests import IntegrationTestCase

from freightmas.portal.print_formats import (
	PORTAL_PRINT_FORMAT_DEFAULTS,
	resolve_portal_print_format,
	validate_portal_print_format,
)


class TestPortalPrintFormats(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self._original_settings = {
			"portal_sales_invoice_print_format": frappe.db.get_single_value(
				"FreightMas Settings", "portal_sales_invoice_print_format"
			),
			"portal_quotation_print_format": frappe.db.get_single_value(
				"FreightMas Settings", "portal_quotation_print_format"
			),
		}
		self._ensure_portal_allowed_defaults()

	def tearDown(self):
		for field, value in self._original_settings.items():
			frappe.db.set_single_value("FreightMas Settings", field, value, update_modified=False)
		super().tearDown()

	def _ensure_portal_allowed_defaults(self):
		for doctype, print_format in PORTAL_PRINT_FORMAT_DEFAULTS.items():
			if not frappe.db.exists("Print Format", print_format):
				continue
			frappe.db.set_value(
				"Print Format",
				print_format,
				"allow_client_portal_download",
				1,
				update_modified=False,
			)
			field = (
				"portal_sales_invoice_print_format"
				if doctype == "Sales Invoice"
				else "portal_quotation_print_format"
			)
			frappe.db.set_single_value("FreightMas Settings", field, print_format, update_modified=False)

	def test_validate_rejects_non_allowed_format(self):
		if not frappe.db.exists("Print Format", "Quotation Cost Sheet"):
			self.skipTest("Quotation Cost Sheet print format not installed")

		with self.assertRaises(frappe.ValidationError):
			validate_portal_print_format("Quotation", "Quotation Cost Sheet")

	def test_validate_rejects_wrong_doctype(self):
		if not frappe.db.exists("Print Format", "FreightMas Quotation"):
			self.skipTest("FreightMas Quotation print format not installed")

		with self.assertRaises(frappe.ValidationError):
			validate_portal_print_format("Sales Invoice", "FreightMas Quotation")

	def test_resolve_uses_allowed_settings_format(self):
		if not frappe.db.exists("Print Format", "FreightMas Sales Invoice"):
			self.skipTest("FreightMas Sales Invoice print format not installed")

		resolved = resolve_portal_print_format("Sales Invoice")
		self.assertEqual(resolved, "FreightMas Sales Invoice")

	def test_resolve_rejects_disallowed_settings_format(self):
		if not frappe.db.exists("Print Format", "Quotation Cost Sheet"):
			self.skipTest("Quotation Cost Sheet print format not installed")

		frappe.db.set_single_value(
			"FreightMas Settings",
			"portal_quotation_print_format",
			"Quotation Cost Sheet",
			update_modified=False,
		)
		with self.assertRaises(frappe.PermissionError):
			resolve_portal_print_format("Quotation")
