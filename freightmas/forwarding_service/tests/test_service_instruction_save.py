# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestServiceInstructionSave(IntegrationTestCase):
	def test_validate_backfills_missing_service_instruction(self):
		name = frappe.db.get_value("Service Order", {"service_instruction": ["is", "not set"]}, "name")
		if not name:
			self.skipTest("No Service Order with empty service_instruction")

		frappe.db.begin()
		try:
			doc = frappe.get_doc("Service Order", name)
			doc.run_method("validate")
			self.assertTrue(doc.service_instruction)
		finally:
			frappe.db.rollback()

	def test_refresh_service_order_scope_persists_instruction(self):
		name = frappe.db.get_value(
			"Service Order",
			[
				["forwarding_job_reference", "is", "set"],
				["service_module", "is", "set"],
				["supplier", "is", "set"],
				["service_module", "!=", "Road Transport"],
			],
			"name",
		)
		if not name:
			self.skipTest("No Service Order found")

		frappe.db.begin()
		try:
			frappe.db.set_value("Service Order", name, "service_instruction", None, update_modified=False)
			from freightmas.forwarding_service.doctype.service_order.service_order import (
				refresh_service_order_scope,
			)

			result = refresh_service_order_scope(name)
			stored = frappe.db.get_value("Service Order", name, "service_instruction")
			self.assertTrue(result.get("service_instruction"))
			self.assertEqual(stored, result.get("service_instruction"))
		finally:
			frappe.db.rollback()

	def test_insert_persists_service_instruction(self):
		job_name = frappe.db.get_value(
			"Forwarding Job",
			{"requires_port_clearance": 1, "docstatus": ["<", 2]},
			"name",
		)
		if not job_name:
			self.skipTest("No suitable Forwarding Job found")

		job = frappe.get_doc("Forwarding Job", job_name)
		supplier = frappe.db.get_value("Supplier", {}, "name")
		charge = frappe.db.get_value("Item", {"disabled": 0}, "name") or "Port Handling Charges"

		frappe.db.begin()
		try:
			doc = frappe.new_doc("Service Order")
			doc.forwarding_job_reference = job.name
			doc.service_module = "Port Clearance"
			doc.supplier = supplier
			doc.order_date = frappe.utils.today()
			doc.terms_and_conditions = "Test terms"
			doc.prepared_by = frappe.session.user
			doc.append("service_order_charges", {
				"charge": charge,
				"qty": 1,
				"buy_rate": 100,
			})
			doc.insert(ignore_permissions=True)

			stored = frappe.db.get_value("Service Order", doc.name, "service_instruction")
			self.assertTrue(stored)
			self.assertIn(supplier, stored)
		finally:
			frappe.db.rollback()
