# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Tests for the client-facing Shipment Tracking PDF report."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from freightmas.forwarding_service.utils.client_tracking_view import build_pdf_job_context
from freightmas.freightmas.page.shipment_dashboard.shipment_dashboard import (
	_build_shipment_tracking_pdf,
	_pdf_jobs_for_customer,
)
from freightmas.tests.test_client_tracking_view import _make_customer, _make_job


class TestShipmentTrackingPdf(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_pdf_jobs_sort_delayed_first_then_by_eta(self):
		customer = _make_customer("SORT1")
		on_time = _make_job(customer, "SORT1a", eta=add_days(nowdate(), 10))
		delayed = _make_job(customer, "SORT1b", eta=add_days(nowdate(), -2))
		frappe.db.set_value("Forwarding Job", delayed.name, "operational_phase", "in_transit")
		delayed.reload()

		jobs = _pdf_jobs_for_customer(customer.name)
		names = [job["ref"] for job in jobs]
		self.assertEqual(names.index(delayed.name), 0)
		self.assertLess(names.index(on_time.name), len(names))

	def test_pdf_template_renders_landscape_layout(self):
		customer = _make_customer("HTML1")
		job = _make_job(
			customer,
			"HTML1",
			customer_reference="PO-HTML-001",
			requires_sea_air_freight=1,
			requires_port_clearance=1,
			is_trucking_required=1,
		)
		frappe.db.set_value(
			"Forwarding Job",
			job.name,
			{
				"current_comment": "Awaiting vessel arrival",
				"port_clearance_tracking_comment": "Customs docs submitted",
				"api_last_event": "Vessel departed Beira",
				"api_last_event_date": nowdate(),
			},
		)
		job.reload()

		ctx = build_pdf_job_context(job)
		html = frappe.render_template(
			"freightmas/templates/shipment_tracking_report.html",
			{
				"company": "Test Co",
				"customer": customer.customer_name,
				"logo": None,
				"jobs": [{**ctx, "num": 1}],
				"generated_on": "28-Aug-26",
				"summary": {"total": 1, "in_transit": 1, "delayed": 0, "line": "1 SHIPMENT · 1 IN TRANSIT"},
			},
		)

		self.assertIn("A4 landscape", html)
		self.assertIn("Shipments at a Glance", html)
		self.assertIn("Detailed per Shipment", html)
		self.assertIn("Shipment Tracking Report", html)
		self.assertIn("Shipments</div>", html)
		self.assertIn("phase-pill", html)
		self.assertIn("PO-HTML-001", html)
		self.assertIn("Vessel departed Beira", html)
		self.assertIn("Customs docs submitted", html)
		self.assertIn("Services", html)
		self.assertIn("Sea / Air Freight", html)
		self.assertIn("Port Clearance", html)
		self.assertIn("BL Number", html)
		self.assertIn("Cargo Count", html)
		self.assertIn("PENDING", html)
		self.assertIn("shipment-card", html)
		self.assertNotIn("Shipment Journey", html)
		self.assertNotIn("Journey progress", html)

	def test_build_shipment_tracking_pdf_returns_bytes(self):
		customer = _make_customer("PDFX1")
		_make_job(customer, "PDFX1")

		pdf, customer_name = _build_shipment_tracking_pdf(customer.name)

		self.assertTrue(customer_name)
		self.assertTrue(pdf.startswith(b"%PDF"))

	def test_pdf_glance_latest_comment_shows_road_counts_and_comment(self):
		customer = _make_customer("ROAD1")
		job = _make_job(
			customer,
			"ROAD1",
			is_trucking_required=1,
		)
		job.append(
			"cargo_parcel_details",
			{
				"cargo_type": "Containerised",
				"container_number": "TRK-R1A",
				"container_type": "40HC",
				"cargo_quantity": 1,
				"is_truck_required": 1,
			},
		)
		job.append(
			"cargo_parcel_details",
			{
				"cargo_type": "Containerised",
				"container_number": "TRK-R1B",
				"container_type": "40HC",
				"cargo_quantity": 1,
				"is_truck_required": 1,
			},
		)
		job.save(ignore_permissions=True)
		row_a, row_b = job.cargo_parcel_details
		frappe.db.set_value("Cargo Parcel Details", row_a.name, "is_loaded", 1)
		frappe.db.set_value("Cargo Parcel Details", row_b.name, {"is_loaded": 1, "is_offloaded": 1})
		frappe.db.set_value(
			"Forwarding Job",
			job.name,
			{
				"operational_phase": "on_road",
				"road_transport_tracking_comment": "Loaded waiting for genset (Beira)",
			},
		)
		job.reload()

		ctx = build_pdf_job_context(job)
		self.assertEqual(
			ctx["glance"]["latest_comment"],
			"2 loaded, 1 offloaded · Loaded waiting for genset (Beira)",
		)
