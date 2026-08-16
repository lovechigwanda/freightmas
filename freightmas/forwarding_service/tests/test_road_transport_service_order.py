# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import unittest

import frappe

from freightmas.forwarding_service.utils.service_order import (
	build_service_order_parcel_row,
	get_parcel_cargo_label,
	get_parcel_display_title,
	get_road_transport_milestones,
	get_road_transport_service_instruction,
	serialize_parcel_for_dialog,
)


def _parcel(**kwargs):
	defaults = {
		"name": "parcel-1",
		"is_truck_required": 1,
		"transporter": "Test Transporter",
		"container_number": "MSCU1234567",
		"container_type": "40HC",
		"cargo_type": "Containerised",
		"service_charge": "Local Transport",
		"truck_buying_rate": 5200,
		"cargo_loading_address": "Beira Port",
		"cargo_offloading_address": "Harare",
		"load_by_date": "2026-07-22",
		"to_be_returned": 0,
		"truck_reg_no": "ABC123",
		"trailer_reg_no": "TRL456",
		"driver_name": "John Driver",
		"border_tracking": 0,
		"border_2_tracking": 0,
		"offloading_point": 0,
		"drop_off_place": "Beira",
	}
	defaults.update(kwargs)
	return frappe._dict(defaults)


class TestRoadTransportServiceOrder(unittest.TestCase):
	def test_get_parcel_cargo_label(self):
		self.assertEqual(get_parcel_cargo_label(_parcel()), "MSCU1234567")
		self.assertEqual(
			get_parcel_cargo_label(_parcel(container_number=None, cargo_item_description="Steel Sheets")),
			"Steel Sheets",
		)

	def test_get_parcel_display_title(self):
		self.assertEqual(get_parcel_display_title(_parcel()), "MSCU1234567 1X 40HC")
		self.assertEqual(
			get_parcel_display_title(_parcel(
				cargo_type="General Cargo",
				container_number=None,
				container_type=None,
				cargo_item_description="Bulk Chrome",
			)),
			"Bulk Chrome",
		)

	def test_milestones_base_sequence(self):
		labels = get_road_transport_milestones([_parcel()])
		self.assertEqual(labels[0], "Is Loaded")
		self.assertIn("Is Offloaded", labels)
		self.assertIn("Is Completed", labels)
		self.assertNotIn("Is Returned", labels)

	def test_milestones_with_extended_tracking_and_return(self):
		labels = get_road_transport_milestones([
			_parcel(
				border_tracking=1,
				border_2_tracking=1,
				offloading_point=1,
				to_be_returned=1,
			)
		])
		self.assertEqual(labels[0], "Is Loaded")
		self.assertIn("Border Arrived", labels)
		self.assertIn("Border 2 Arrived", labels)
		self.assertIn("Offloading Point Arrived", labels)
		self.assertLess(labels.index("Is Loaded"), labels.index("Border Arrived"))
		self.assertLess(labels.index("Offloading Point Arrived"), labels.index("Is Offloaded"))
		self.assertIn("Is Returned", labels)
		self.assertEqual(labels[-1], "Is Completed")

	def test_milestones_for_service_order_use_parcel_tracking_flags(self):
		from freightmas.forwarding_service.utils.service_order import (
			get_road_transport_milestones_for_service_order,
		)

		so = frappe._dict({
			"service_order_parcels": [
				frappe._dict({"border_tracking": 0, "border_2_tracking": 0, "offloading_point": 0, "to_be_returned": 0}),
				frappe._dict({"border_tracking": 1, "border_2_tracking": 0, "offloading_point": 1, "to_be_returned": 1}),
			]
		})
		labels = get_road_transport_milestones_for_service_order(so)
		self.assertIn("Border Arrived", labels)
		self.assertIn("Offloading Point Arrived", labels)
		self.assertIn("Is Returned", labels)

	def test_service_instruction_is_generic(self):
		job = frappe._dict({"destination": "Harare", "loading_address": "Default Loading"})
		text = get_road_transport_service_instruction("MA Inc.", job, [_parcel()])
		self.assertIn("MA Inc.", text)
		self.assertIn("cargo detailed below", text)
		self.assertIn("tracking updates", text)
		self.assertNotIn("Beira Port", text)
		self.assertNotIn("Harare", text)

	def test_build_service_order_parcel_row_snapshot(self):
		row = build_service_order_parcel_row(_parcel(border_tracking=1))
		self.assertEqual(row["cargo_parcel_reference"], "parcel-1")
		self.assertEqual(row["cargo_label"], "MSCU1234567 1X 40HC")
		self.assertEqual(row["container_number"], "MSCU1234567")
		self.assertEqual(row["container_type"], "40HC")
		self.assertEqual(row["cargo_type"], "Containerised")
		self.assertEqual(row["transporter_rate"], 5200)
		self.assertEqual(row["border_tracking"], 1)
		self.assertEqual(row["drop_off_place"], "Beira")

	def test_serialize_parcel_flags_validation_errors(self):
		data = serialize_parcel_for_dialog(_parcel(service_charge=None, truck_buying_rate=0))
		self.assertTrue(data["validation_errors"])


class TestRoadTransportServiceOrderIntegration(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		if not frappe.db:
			raise unittest.SkipTest("Requires an active Frappe site connection")

	def test_create_road_transport_service_order_from_parcels(self):
		job_name = frappe.db.get_value(
			"Forwarding Job",
			{"is_trucking_required": 1, "docstatus": ["<", 2]},
			"name",
		)
		if not job_name:
			self.skipTest("No trucking Forwarding Job found")

		job = frappe.get_doc("Forwarding Job", job_name)
		parcels = [
			row for row in job.get("cargo_parcel_details") or []
			if row.get("is_truck_required") and row.get("transporter")
			and row.get("service_charge") and row.get("truck_buying_rate")
		]
		if not parcels:
			self.skipTest("No eligible trucking parcels on job")

		transporter = parcels[0].transporter
		parcel_names = [p.name for p in parcels if p.transporter == transporter][:1]

		frappe.db.begin()
		try:
			from freightmas.forwarding_service.doctype.service_order.service_order import (
				create_service_order_from_job,
			)

			so_name = create_service_order_from_job(
				job_name,
				"Road Transport",
				transporter,
				parcel_names=parcel_names,
			)
			so = frappe.get_doc("Service Order", so_name)
			self.assertEqual(so.service_module, "Road Transport")
			self.assertTrue(so.get("service_order_parcels"))
			self.assertTrue(so.service_instruction)
			self.assertTrue(so.tracking_milestones)
			self.assertEqual(len(so.service_order_charges), len(parcel_names))
			self.assertEqual(so.service_order_charges[0].cargo_parcel_reference, parcel_names[0])
		finally:
			frappe.db.rollback()
