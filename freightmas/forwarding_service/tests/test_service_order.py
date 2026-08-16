# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import unittest

import frappe

from freightmas.forwarding_service.utils.service_order import (
	build_scope_of_work,
	get_enabled_service_modules,
	get_service_instruction,
	get_scope_print_layout,
	is_service_module_enabled,
	validate_cost_rows_have_submitted_service_order,
)
from freightmas.forwarding_service.utils.service_order_settings import (
	service_order_required_before_pi,
	service_orders_enabled,
)


def _job(**kwargs):
	return frappe._dict(kwargs)


class TestServiceOrderLogic(unittest.TestCase):
	def test_get_enabled_service_modules(self):
		job = _job(
			requires_sea_air_freight=1,
			requires_port_clearance=1,
			is_trucking_required=0,
			requires_border_clearance=0,
			requires_warehousing=0,
			shipment_mode="Sea",
		)
		modules = get_enabled_service_modules(job)
		self.assertIn("Sea/Air Freight", modules)
		self.assertIn("Port Clearance", modules)
		self.assertNotIn("Road Transport", modules)

	def test_road_freight_module_when_road_mode(self):
		job = _job(
			requires_sea_air_freight=0,
			requires_port_clearance=0,
			is_trucking_required=0,
			requires_border_clearance=0,
			requires_warehousing=0,
			shipment_mode="Road",
		)
		modules = get_enabled_service_modules(job)
		self.assertIn("Road Freight", modules)
		self.assertTrue(is_service_module_enabled(job, "Road Freight"))

	def test_build_scope_of_work_excludes_customer_and_uses_two_columns(self):
		job = _job(
			name="FWJB-TEST-001",
			customer="Test Customer",
			customer_reference="CUST-REF-1",
			cargo_description="General cargo",
			port_of_loading="Durban",
			port_of_discharge="Harare",
			direction="Import",
			requires_port_clearance=1,
			bl_number="BL123",
			shipping_line="MSC",
			cargo_count="2x40HC",
			port_clearance_milestones=[],
		)
		scope = build_scope_of_work(job, "Port Clearance", "Test Supplier")
		layout = get_scope_print_layout(job, "Port Clearance", "Test Supplier")
		self.assertIn("FWJB-TEST-001", scope)
		self.assertIn("BL123", scope)
		self.assertNotIn("Test Customer", scope)
		self.assertNotIn("CUST-REF-1", scope)
		self.assertEqual(len(layout["grid_columns"]), 3)
		statement = get_service_instruction("Test Supplier", "Port Clearance", job)
		self.assertIn("Test Supplier", statement)
		self.assertIn("Harare", statement)
		self.assertIn("nominate", statement)
		self.assertIn("service_instruction", layout)


class TestServiceOrderSettings(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		if not frappe.db:
			raise unittest.SkipTest("Requires an active Frappe site connection")

	def test_validate_cost_rows_gate_when_not_required(self):
		original_required = frappe.db.get_single_value(
			"FreightMas Settings", "require_service_order_before_pi"
		)
		original_enabled = frappe.db.get_single_value("FreightMas Settings", "enable_service_orders")
		frappe.db.set_single_value("FreightMas Settings", "enable_service_orders", 0)
		frappe.db.set_single_value("FreightMas Settings", "require_service_order_before_pi", 0)
		try:
			self.assertFalse(service_order_required_before_pi())
			rows = [_job(name="row-1", service_order_reference=None)]
			validate_cost_rows_have_submitted_service_order(rows)
		finally:
			frappe.db.set_single_value(
				"FreightMas Settings", "require_service_order_before_pi", original_required or 0
			)
			frappe.db.set_single_value(
				"FreightMas Settings", "enable_service_orders", original_enabled or 0
			)

	def test_validate_cost_rows_gate_throws_when_required(self):
		original_required = frappe.db.get_single_value(
			"FreightMas Settings", "require_service_order_before_pi"
		)
		original_enabled = frappe.db.get_single_value("FreightMas Settings", "enable_service_orders")
		frappe.db.set_single_value("FreightMas Settings", "enable_service_orders", 1)
		frappe.db.set_single_value("FreightMas Settings", "require_service_order_before_pi", 1)
		try:
			rows = [_job(name="row-1", service_order_reference=None)]
			self.assertTrue(service_order_required_before_pi())
			with self.assertRaises(frappe.ValidationError):
				validate_cost_rows_have_submitted_service_order(rows)
		finally:
			frappe.db.set_single_value(
				"FreightMas Settings", "require_service_order_before_pi", original_required or 0
			)
			frappe.db.set_single_value(
				"FreightMas Settings", "enable_service_orders", original_enabled or 0
			)

	def test_settings_helpers(self):
		original_enabled = frappe.db.get_single_value("FreightMas Settings", "enable_service_orders")
		frappe.db.set_single_value("FreightMas Settings", "enable_service_orders", 1)
		self.assertTrue(service_orders_enabled())
		frappe.db.set_single_value("FreightMas Settings", "enable_service_orders", 0)
		self.assertFalse(service_orders_enabled())
		frappe.db.set_single_value(
			"FreightMas Settings", "enable_service_orders", original_enabled or 0
		)
