# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Client Portal dashboard overview tests."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate
from unittest.mock import patch

from freightmas.portal.api import dashboard as portal_dashboard
from freightmas.portal.api import profile as portal_profile
from freightmas.tests.test_client_portal_shipments import _make_pair


class TestPortalDashboardOverview(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_get_overview_returns_enriched_dashboard_sections(self):
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D1")
		frappe.db.set_value("Forwarding Job", job_a.name, "operational_phase", "in_transit")
		frappe.db.set_value("Forwarding Job", job_a.name, "current_comment", "Awaiting vessel update")
		frappe.db.set_value("Forwarding Job", job_a.name, "eta", add_days(nowdate(), -2))
		job_a.reload()
		job_a.append(
			"tracking_timeline",
			{"event": "Departed origin", "date": nowdate(), "source": "Manual"},
		)
		job_a.save(ignore_permissions=True)

		frappe.set_user(user_a.name)
		try:
			result = portal_dashboard.get_overview()
		finally:
			frappe.set_user("Administrator")

		for key in (
			"phase_pipeline",
			"active_count",
			"delayed_count",
			"arriving_soon_count",
			"attention_count",
			"attention_items",
			"in_motion_jobs",
			"financial_snapshot",
			"outstanding_amount",
			"overdue_amount",
			"paid_ytd",
		):
			self.assertIn(key, result)

		self.assertGreaterEqual(result["active_count"], 1)
		self.assertGreaterEqual(result["delayed_count"], 1)
		self.assertGreaterEqual(result["attention_count"], 1)
		delayed_items = [row for row in result["attention_items"] if row["type"] == "delayed_shipment"]
		self.assertTrue(any(row["job_name"] == job_a.name for row in delayed_items))
		attention_job_names = {row["job_name"] for row in result["attention_items"] if row.get("job_name")}
		for job in result["in_motion_jobs"]:
			self.assertNotIn(job["name"], attention_job_names)
		self.assertIn("overdue_invoice_count", result["financial_snapshot"])

	def test_get_overview_scopes_delayed_jobs_to_own_customer(self):
		customer_a, _customer_b, user_a, job_a, job_b = _make_pair("D2")
		frappe.db.set_value("Forwarding Job", job_a.name, "eta", add_days(nowdate(), -1))
		frappe.db.set_value("Forwarding Job", job_b.name, "eta", add_days(nowdate(), -1))

		frappe.set_user(user_a.name)
		try:
			result = portal_dashboard.get_overview()
		finally:
			frappe.set_user("Administrator")

		delayed_items = [row for row in result["attention_items"] if row["type"] == "delayed_shipment"]
		attention_names = {row["job_name"] for row in delayed_items}
		self.assertIn(job_a.name, attention_names)
		self.assertNotIn(job_b.name, attention_names)

	def test_get_profile_returns_portal_logo_url_not_private_file_path(self):
		_customer_a, _customer_b, user_a, _job_a, _job_b = _make_pair("D3")
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		original_logo = frappe.db.get_value("Company", company, "company_logo")
		frappe.db.set_value("Company", company, "company_logo", "/private/files/test-logo.png")

		frappe.set_user(user_a.name)
		try:
			result = portal_profile.get_profile()
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Company", company, "company_logo", original_logo)

		self.assertEqual(
			result["branding"]["logo"],
			"/api/method/freightmas.portal.api.profile.get_company_logo",
		)
		self.assertNotIn("/private/files/", result["branding"]["logo"] or "")

	def test_get_company_logo_streams_image_bytes(self):
		_customer_a, _customer_b, user_a, _job_a, _job_b = _make_pair("D4")
		fake_bytes = b"\x89PNG\r\n\x1a\n"

		with patch(
			"freightmas.portal.api.profile.read_company_logo_bytes",
			return_value=(fake_bytes, "image/png", "logo.png"),
		):
			frappe.set_user(user_a.name)
			try:
				portal_profile.get_company_logo()
			finally:
				frappe.set_user("Administrator")

		self.assertEqual(frappe.local.response.type, "binary")
		self.assertEqual(frappe.local.response.filecontent, fake_bytes)
		self.assertEqual(frappe.local.response.filename, "logo.png")
		self.assertEqual(frappe.local.response["Content-Type"], "image/png")
