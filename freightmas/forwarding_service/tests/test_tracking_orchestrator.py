# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Tests for phase-driven tracking headline orchestration."""

import unittest

import frappe

from freightmas.forwarding_service.utils.tracking_orchestrator import (
	SERVICE_PORT_CLEARANCE,
	api_owns_job_narrative,
	append_service_comment_to_timeline,
	build_road_client_headline,
	resolve_client_headline,
	road_milestone_count_summary,
	sync_current_comment,
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
		"api_last_event": None,
		"api_last_event_date": None,
		"current_comment": None,
		"port_clearance_tracking_comment": None,
		"road_transport_tracking_comment": None,
		"border_clearance_tracking_comment": None,
		"warehouse_tracking_comment": None,
		"cargo_parcel_details": [],
		"port_clearance_milestones": [],
		"border_clearance_milestones": [],
		"warehouse_milestones": [],
		"road_freight_milestones": [],
		"tracking_timeline": [],
	})
	doc.update(kwargs)
	return doc


def _truck_parcel(**kwargs):
	row = frappe._dict({
		"is_truck_required": 1,
		"is_booked": 0,
		"is_loaded": 0,
		"is_offloaded": 0,
		"is_returned": 0,
		"is_completed": 0,
		"border_arrived_on": None,
		"border_2_arrived_on": None,
		"offloading_arrived_on": None,
	})
	row.update(kwargs)
	return row


class TestTrackingOrchestrator(unittest.TestCase):
	def test_port_clearance_headline_from_service_comment(self):
		doc = _job(
			requires_port_clearance=1,
			ata="2026-02-01",
			port_clearance_tracking_comment="DO obtained, entry filed",
			port_clearance_milestones=[frappe._dict({"is_completed": 0})],
			cargo_parcel_details=[frappe._dict({"cargo_type": "Containerised", "gate_out_date": None})],
		)
		self.assertEqual(resolve_client_headline(doc), "DO obtained, entry filed")

	def test_port_clearance_headline_fallback_to_phase_label(self):
		doc = _job(
			requires_port_clearance=1,
			ata="2026-02-01",
			port_clearance_milestones=[frappe._dict({"is_completed": 0})],
			cargo_parcel_details=[frappe._dict({"cargo_type": "Containerised", "gate_out_date": None})],
		)
		self.assertEqual(resolve_client_headline(doc), "Under Port Clearance")

	def test_border_clearance_headline(self):
		doc = _job(
			requires_port_clearance=1,
			requires_border_clearance=1,
			ata="2026-02-01",
			border_clearance_tracking_comment="At Beitbridge border",
			port_clearance_milestones=[frappe._dict({"is_completed": 1})],
			border_clearance_milestones=[frappe._dict({"is_completed": 0})],
		)
		self.assertEqual(resolve_client_headline(doc), "At Beitbridge border")

	def test_warehouse_headline(self):
		doc = _job(
			requires_warehousing=1,
			warehouse_tracking_comment="Cargo stored in bonded warehouse",
			warehouse_milestones=[frappe._dict({"is_completed": 0})],
		)
		self.assertEqual(resolve_client_headline(doc), "Cargo stored in bonded warehouse")

	def test_road_milestone_count_summary_across_parcels(self):
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[
				_truck_parcel(is_booked=1, is_loaded=1),
				_truck_parcel(is_booked=1, is_loaded=1, is_offloaded=1),
				_truck_parcel(is_booked=1),
			],
		)
		self.assertEqual(
			road_milestone_count_summary(doc),
			"1 booked, 1 loaded, 1 offloaded",
		)

	def test_road_milestone_count_summary_includes_extended_stages(self):
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[
				_truck_parcel(
					is_loaded=1,
					border_arrived_on="2026-02-01",
					border_2_arrived_on="2026-02-02",
					offloading_arrived_on="2026-02-03",
				),
				_truck_parcel(is_loaded=1, border_arrived_on="2026-02-01"),
			],
		)
		self.assertEqual(
			road_milestone_count_summary(doc),
			"1 at border, 1 at offloading point",
		)

	def test_road_milestone_count_summary_five_loaded(self):
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[_truck_parcel(is_loaded=1) for _ in range(5)],
		)
		self.assertEqual(road_milestone_count_summary(doc), "5 loaded")

	def test_road_milestone_count_summary_four_loaded_one_at_border(self):
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[
				*[_truck_parcel(is_loaded=1) for _ in range(4)],
				_truck_parcel(is_loaded=1, border_arrived_on="2026-02-01"),
			],
		)
		self.assertEqual(road_milestone_count_summary(doc), "4 loaded, 1 at border")

	def test_road_milestone_count_summary_single_container_omits_count(self):
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[_truck_parcel(is_loaded=1)],
		)
		self.assertEqual(road_milestone_count_summary(doc), "Loaded")

	def test_road_milestone_count_summary_single_container_highest_stage_only(self):
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[_truck_parcel(
				is_booked=1,
				is_loaded=1,
				border_arrived_on="2026-02-01",
				offloading_arrived_on="2026-02-02",
				is_offloaded=1,
			)],
		)
		self.assertEqual(road_milestone_count_summary(doc), "Offloaded")

	def test_on_road_headline_counts_plus_comment(self):
		doc = _job(
			is_trucking_required=1,
			road_transport_tracking_comment="Loaded waiting for genset (Beira)",
			cargo_parcel_details=[
				_truck_parcel(is_loaded=1),
				_truck_parcel(is_loaded=1),
				_truck_parcel(is_loaded=1, is_offloaded=1),
			],
		)
		self.assertEqual(
			resolve_client_headline(doc),
			"2 loaded, 1 offloaded · Loaded waiting for genset (Beira)",
		)

	def test_on_road_headline_counts_only_when_comment_empty(self):
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[
				_truck_parcel(is_loaded=1),
				_truck_parcel(is_offloaded=1),
			],
		)
		self.assertEqual(resolve_client_headline(doc), "1 loaded, 1 offloaded")

	def test_on_road_headline_comment_only_when_no_milestones(self):
		doc = _job(
			is_trucking_required=1,
			road_transport_tracking_comment="Transport booked, awaiting loading",
			cargo_parcel_details=[_truck_parcel(is_loaded=1, is_completed=0)],
		)
		# Parcel is loaded so phase is on_road; no milestone flags set except loaded
		doc.cargo_parcel_details[0].is_loaded = 0
		self.assertEqual(
			build_road_client_headline(doc),
			"Transport booked, awaiting loading",
		)

	def test_build_road_client_headline_returns_none_without_parcels_or_comment(self):
		doc = _job(is_trucking_required=1)
		self.assertIsNone(build_road_client_headline(doc))

	def test_sea_air_headline_from_api_last_event(self):
		doc = _job(
			atd="2026-01-10",
			ata=None,
			api_last_event="Vessel departed",
			api_last_event_date="2026-01-10",
		)
		headline = resolve_client_headline(doc)
		self.assertIn("Vessel departed", headline)

	def test_api_stops_owning_narrative_after_port_clearance_comment(self):
		doc = _job(
			requires_port_clearance=1,
			ata="2026-02-01",
			port_clearance_tracking_comment="Clearance started",
			port_clearance_milestones=[frappe._dict({"is_completed": 0})],
			cargo_parcel_details=[frappe._dict({"cargo_type": "Containerised", "gate_out_date": None})],
		)
		self.assertFalse(api_owns_job_narrative(doc))

	def test_api_owns_narrative_in_transit(self):
		doc = _job(atd="2026-01-10", ata=None)
		self.assertTrue(api_owns_job_narrative(doc))

	def test_sync_current_comment_sets_headline(self):
		doc = _job(
			requires_port_clearance=1,
			ata="2026-02-01",
			port_clearance_tracking_comment="Waiting for DO",
			port_clearance_milestones=[frappe._dict({"is_completed": 0})],
			cargo_parcel_details=[frappe._dict({"cargo_type": "Containerised", "gate_out_date": None})],
		)
		sync_current_comment(doc)
		self.assertEqual(doc.current_comment, "Waiting for DO")

	def test_append_service_comment_to_timeline(self):
		doc = _job()
		append_service_comment_to_timeline(doc, "DO received", SERVICE_PORT_CLEARANCE)
		self.assertEqual(len(doc.tracking_timeline), 1)
		self.assertEqual(doc.tracking_timeline[0].service, SERVICE_PORT_CLEARANCE)
		self.assertEqual(doc.tracking_timeline[0].event, "DO received")

	def test_delivered_headline(self):
		doc = _job(
			status="Delivered",
			is_trucking_required=1,
			cargo_parcel_details=[frappe._dict({
				"is_truck_required": 1,
				"is_completed": 1,
			})],
		)
		self.assertEqual(resolve_client_headline(doc), "Delivered")
