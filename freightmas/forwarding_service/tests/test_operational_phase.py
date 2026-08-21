# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Unit tests for Forwarding Job operational phase derivation."""

import unittest

import frappe

from freightmas.forwarding_service.utils.operational_phase import (
	derive_operational_phase,
	get_overview_bucket_phases,
)


def _job(**kwargs):
	doc = frappe._dict({
		"status": "In Progress",
		"direction": "Import",
		"shipment_mode": "Sea",
		"requires_sea_air_freight": 1,
		"requires_port_clearance": 0,
		"requires_border_clearance": 0,
		"is_trucking_required": 0,
		"requires_warehousing": 0,
		"atd": None,
		"ata": None,
		"discharge_date": None,
		"cargo_parcel_details": [],
		"port_clearance_milestones": [],
		"border_clearance_milestones": [],
		"warehouse_milestones": [],
		"road_freight_milestones": [],
	})
	doc.update(kwargs)
	return doc


class TestOperationalPhase(unittest.TestCase):
	def test_draft_is_planning(self):
		result = derive_operational_phase(_job(status="Draft"))
		self.assertEqual(result["phase"], "planning")

	def test_cancelled(self):
		result = derive_operational_phase(_job(status="Cancelled"))
		self.assertEqual(result["phase"], "cancelled")

	def test_closed(self):
		result = derive_operational_phase(_job(status="Completed"))
		self.assertEqual(result["phase"], "closed")

	def test_in_transit_after_departure(self):
		result = derive_operational_phase(_job(atd="2026-01-10", ata=None))
		self.assertEqual(result["phase"], "in_transit")

	def test_at_terminal_after_arrival(self):
		result = derive_operational_phase(_job(
			atd="2026-01-10",
			ata="2026-02-01",
			cargo_parcel_details=[frappe._dict({
				"cargo_type": "Containerised",
				"gate_out_date": None,
			})],
		))
		self.assertEqual(result["phase"], "at_terminal")

	def test_under_port_clearance(self):
		result = derive_operational_phase(_job(
			requires_port_clearance=1,
			ata="2026-02-01",
			port_clearance_milestones=[frappe._dict({
				"is_completed": 0,
				"stage": "Documentation",
				"stage_sequence": 1,
			})],
			cargo_parcel_details=[frappe._dict({
				"cargo_type": "Containerised",
				"gate_out_date": None,
			})],
		))
		self.assertEqual(result["phase"], "under_port_clearance")
		self.assertEqual(result["substage"], "Documentation")

	def test_under_border_clearance_after_port_complete(self):
		result = derive_operational_phase(_job(
			requires_port_clearance=1,
			requires_border_clearance=1,
			ata="2026-02-01",
			port_clearance_milestones=[frappe._dict({
				"is_completed": 1,
				"stage": "Documentation",
				"stage_sequence": 1,
			})],
			border_clearance_milestones=[frappe._dict({
				"is_completed": 0,
				"stage": "Customs",
				"stage_sequence": 2,
			})],
		))
		self.assertEqual(result["phase"], "under_border_clearance")
		self.assertEqual(result["substage"], "Customs")

	def test_on_road_when_trucking_started(self):
		result = derive_operational_phase(_job(
			is_trucking_required=1,
			cargo_parcel_details=[frappe._dict({
				"is_truck_required": 1,
				"is_loaded": 1,
				"is_completed": 0,
			})],
		))
		self.assertEqual(result["phase"], "on_road")

	def test_delivered_when_all_trucking_complete(self):
		result = derive_operational_phase(_job(
			is_trucking_required=1,
			cargo_parcel_details=[frappe._dict({
				"is_truck_required": 1,
				"is_completed": 1,
			})],
		))
		self.assertEqual(result["phase"], "delivered")

	def test_overview_bucket_phases_at_origin(self):
		phases = get_overview_bucket_phases("at_origin")
		self.assertEqual(phases, ["planning", "awaiting_departure"])

	def test_overview_pipeline_has_seven_buckets(self):
		from freightmas.forwarding_service.utils.operational_phase import OVERVIEW_PIPELINE_BUCKETS
		self.assertEqual(len(OVERVIEW_PIPELINE_BUCKETS), 7)
		self.assertEqual(OVERVIEW_PIPELINE_BUCKETS[0]["label"], "At Origin")
		self.assertEqual(OVERVIEW_PIPELINE_BUCKETS[2]["label"], "At POD")
		self.assertEqual(OVERVIEW_PIPELINE_BUCKETS[2]["title"], "At Port of Discharge")
		self.assertEqual(OVERVIEW_PIPELINE_BUCKETS[3]["label"], "Port Clearance")
		self.assertEqual(OVERVIEW_PIPELINE_BUCKETS[-1]["label"], "Delivered")


if __name__ == "__main__":
	unittest.main()
