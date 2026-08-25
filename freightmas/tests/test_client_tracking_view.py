# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Tests for build_client_tracking_view() — dossier-shaped tracking payload."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from freightmas.forwarding_service.utils.client_tracking_view import (
	build_client_tracking_view,
	dossier_status_key,
	resolve_client_milestone_report_mode,
)
from freightmas.portal.api import shipments as portal_shipments


def _make_customer(suffix):
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"Tracking View Test Customer {suffix}",
			"customer_type": "Company",
			"customer_group": "Commercial",
			"territory": "Zimbabwe",
		}
	)
	customer.insert(ignore_permissions=True)
	return customer


def _make_job(customer, suffix, **overrides):
	data = {
		"doctype": "Forwarding Job",
		"company": "Maita",
		"created_by": "Administrator",
		"naming_series": "FWJB-.#####.-.YY.",
		"shipment_mode": "Sea",
		"incoterms": "CIF",
		"direction": "Import",
		"shipment_type": "FCL",
		"customer": customer.name,
		"customer_reference": f"TRK-VIEW-{suffix}",
		"consignee": customer.name,
		"port_of_loading": "Beira",
		"port_of_discharge": "Harare",
		"destination": "Harare",
		"eta": add_days(nowdate(), 5),
		"status": "Draft",
	}
	data.update(overrides)
	job = frappe.get_doc(data)
	job.insert(ignore_permissions=True)
	if data.get("status") != "Draft":
		frappe.db.set_value("Forwarding Job", job.name, "status", data["status"])
		job.status = data["status"]
	return job


class TestClientTrackingView(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_banner_includes_phase_and_progress(self):
		customer = _make_customer("B1")
		job = _make_job(customer, "B1")
		frappe.db.set_value("Forwarding Job", job.name, "operational_phase", "in_transit")
		frappe.db.set_value("Forwarding Job", job.name, "current_comment", "Vessel departed Beira")
		job.reload()

		view = build_client_tracking_view(job, milestone_report_mode="Stage Summary", milestone_percent=42)

		self.assertEqual(view["banner"]["status_label"], "In Progress")
		self.assertEqual(view["banner"]["operational_phase"], "in_transit")
		self.assertEqual(view["banner"]["progress_percent"], 42)
		self.assertEqual(view["banner"]["latest_update"], "Vessel departed Beira")
		self.assertEqual(view["banner"]["key_date_label"], "ETA")

	def test_delayed_status_when_eta_passed_without_ata(self):
		customer = _make_customer("B2")
		job = _make_job(customer, "B2")
		frappe.db.set_value("Forwarding Job", job.name, "eta", add_days(nowdate(), -3))
		job.reload()

		self.assertEqual(dossier_status_key(job), "red")
		view = build_client_tracking_view(job)
		self.assertEqual(view["banner"]["status_key"], "red")
		self.assertEqual(view["banner"]["status_label"], "Delayed")

	def test_sections_always_include_sea_air_and_completion(self):
		customer = _make_customer("S1")
		job = _make_job(customer, "S1")
		view = build_client_tracking_view(job)

		kinds = [s["kind"] for s in view["sections"]]
		self.assertEqual(kinds[0], "sea_air")
		self.assertEqual(kinds[-1], "completion")
		self.assertIn("shipment_stages", view["sections"][0])

	def test_road_section_only_when_trucking_required(self):
		customer = _make_customer("R1")
		job = _make_job(customer, "R1")
		job.append(
			"cargo_parcel_details",
			{
				"cargo_type": "Containerised",
				"container_number": "TRK-R1",
				"container_type": "20SD",
				"cargo_quantity": 1,
			},
		)
		job.save(ignore_permissions=True)
		row = job.cargo_parcel_details[-1]

		view = build_client_tracking_view(job)
		self.assertNotIn("road", [s["kind"] for s in view["sections"]])

		frappe.db.set_value("Cargo Parcel Details", row.name, "is_truck_required", 1)
		job.reload()
		view = build_client_tracking_view(job)
		road = next(s for s in view["sections"] if s["kind"] == "road")
		self.assertEqual(len(road["containers"]), 1)

	def test_port_clearance_stage_summary_vs_full_milestones(self):
		customer = _make_customer("C1")
		job = _make_job(customer, "C1")
		frappe.db.set_value("Forwarding Job", job.name, "requires_port_clearance", 1)
		job.reload()
		job.save(ignore_permissions=True)
		job.reload()
		self.assertTrue(job.port_clearance_milestones)

		stage_view = build_client_tracking_view(job, milestone_report_mode="Stage Summary")
		port_stage = next(s for s in stage_view["sections"] if s["title"] == "Port Clearance")
		if any(m.get("stage") for m in job.port_clearance_milestones):
			self.assertEqual(port_stage["kind"], "clearance_stages")
			self.assertTrue(port_stage["stages"])
		else:
			self.assertEqual(port_stage["kind"], "clearance_checklist")

		full_view = build_client_tracking_view(job, milestone_report_mode="Full Milestones")
		port_full = next(s for s in full_view["sections"] if s["title"] == "Port Clearance")
		self.assertEqual(port_full["kind"], "clearance_checklist")
		self.assertEqual(len(port_full["entries"]), len(job.port_clearance_milestones))

	def test_live_updates_from_tracking_timeline_only(self):
		customer = _make_customer("L1")
		job = _make_job(customer, "L1")
		job.append(
			"tracking_timeline",
			{"event": "Container gated out", "date": nowdate(), "source": "Manual"},
		)
		job.append(
			"tracking_timeline",
			{"event": "Vessel arrived", "date": add_days(nowdate(), -1), "source": "API"},
		)
		job.save(ignore_permissions=True)
		job.reload()

		view = build_client_tracking_view(job)
		self.assertEqual(len(view["live_updates"]), 2)
		self.assertEqual(view["live_updates"][0]["event"], "Vessel arrived")
		self.assertEqual(view["live_updates"][1]["event"], "Container gated out")

	def test_portal_get_job_detail_returns_tracking_view(self):
		from freightmas.tests.test_client_portal_shipments import _make_pair

		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("TV1")

		frappe.set_user(user_a.name)
		try:
			result = portal_shipments.get_job_detail(job_a.name)
		finally:
			frappe.set_user("Administrator")

		self.assertIn("tracking_view", result)
		self.assertIn("banner", result["tracking_view"])
		self.assertIn("sections", result["tracking_view"])
		self.assertIn("live_updates", result["tracking_view"])
		self.assertNotIn("milestone_stages", result)
		self.assertNotIn("tracking", result)
		self.assertIn("operational_phase", result["header"])
		self.assertIn("milestone_percent", result["header"])

	def test_resolve_client_milestone_report_mode_customer_override(self):
		customer = _make_customer("M1")
		frappe.db.set_value(
			"Customer",
			customer.name,
			"custom_client_report_milestone_detail",
			"Stage Summary",
		)
		self.assertEqual(resolve_client_milestone_report_mode(customer.name), "Stage Summary")
