# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Tests for phase-driven tracking headline orchestration."""

import unittest

import frappe

from freightmas.forwarding_service.utils.tracking_orchestrator import (
	SERVICE_PORT_CLEARANCE,
	api_owns_job_narrative,
	append_service_comment_to_timeline,
	resolve_client_headline,
	rollup_road_headline,
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

	def test_on_road_headline_from_parcel_comment(self):
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[frappe._dict({
				"is_truck_required": 1,
				"is_loaded": 1,
				"is_completed": 0,
				"tracking_comment": "En route to Harare",
				"updated_on": frappe.utils.now_datetime(),
			})],
		)
		self.assertEqual(resolve_client_headline(doc), "En route to Harare")

	def test_rollup_road_headline_picks_latest_updated(self):
		from frappe.utils import add_to_date, now_datetime

		older = add_to_date(now_datetime(), hours=-2)
		newer = now_datetime()
		doc = _job(
			is_trucking_required=1,
			cargo_parcel_details=[
				frappe._dict({
					"is_truck_required": 1,
					"is_loaded": 1,
					"tracking_comment": "Older update",
					"updated_on": older,
				}),
				frappe._dict({
					"is_truck_required": 1,
					"is_loaded": 1,
					"tracking_comment": "Latest update",
					"updated_on": newer,
				}),
			],
		)
		self.assertEqual(rollup_road_headline(doc), "Latest update")

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
