# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Phase 1 cross-tenant tests for the Client Portal shipments/dashboard API.

Two customers, two Forwarding Jobs, two provisioned portal users - every
endpoint must return customer A's own data and reject any attempt to read
customer B's, whether by an explicit docname or via an unfiltered list.

Also includes a regression guard: the internal (Desk-facing) shipment
dashboard must still return unfiltered, cross-customer data after the
portal's changes land - proving Phase 1 never touched internal access.

Each test builds its own fixtures with a suffix unique to that test method
(rather than sharing a setUp()): this suite observed that IntegrationTestCase
does not roll back between individual test methods in this environment, only
at class teardown, so identically-named fixtures across methods collide.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from freightmas.freightmas.page.shipment_dashboard import shipment_dashboard
from freightmas.portal.api import dashboard as portal_dashboard
from freightmas.portal.api import shipments as portal_shipments


def _make_customer(suffix):
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"Portal Shipments Test Customer {suffix}",
			"customer_type": "Company",
			"customer_group": "Commercial",
			"territory": "Zimbabwe",
		}
	)
	customer.insert(ignore_permissions=True)
	return customer


def _make_user_and_contact(suffix, customer):
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": f"portal.shp.{suffix}@example.com",
			"first_name": f"Portal Shipments {suffix}",
			"send_welcome_email": 0,
		}
	)
	user.insert(ignore_permissions=True)

	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": user.first_name,
			"user": user.name,
			"email_ids": [{"email_id": user.email, "is_primary": 1}],
		}
	)
	contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	contact.insert(ignore_permissions=True)

	return user


def _make_forwarding_job(customer, suffix, status="In Progress"):
	# Inserted as Draft: the controller's ensure_planned_charges_before_status_
	# change() blocks leaving Draft without planned revenue/cost charges, which
	# is irrelevant to these read-path scoping tests. Force the status directly
	# at the DB level afterwards instead of wiring up charges just to satisfy it.
	job = frappe.get_doc(
		{
			"doctype": "Forwarding Job",
			"company": "Maita",
			"created_by": "Administrator",
			"naming_series": "FWJB-.#####.-.YY.",
			"shipment_mode": "Sea",
			"incoterms": "CIF",
			"direction": "Import",
			"shipment_type": "FCL",
			"customer": customer.name,
			"customer_reference": f"PO-PORTAL-TEST-{suffix}",
			"consignee": customer.name,
			"port_of_loading": "Beira",
			"port_of_discharge": "Harare",
			"destination": "Harare",
			"eta": add_days(nowdate(), 5),
			"status": "Draft",
		}
	)
	job.insert(ignore_permissions=True)
	if status != "Draft":
		frappe.db.set_value("Forwarding Job", job.name, "status", status)
		job.status = status
	return job


def _make_pair(suffix):
	"""Two customers + a job each + one portal user provisioned for A."""
	customer_a = _make_customer(f"{suffix}a")
	customer_b = _make_customer(f"{suffix}b")
	user_a = _make_user_and_contact(f"{suffix}a", customer_a)
	job_a = _make_forwarding_job(customer_a, f"{suffix}a")
	job_b = _make_forwarding_job(customer_b, f"{suffix}b")
	return customer_a, customer_b, user_a, job_a, job_b


class TestPortalShipmentsCrossTenant(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_get_jobs_returns_only_own_customer_jobs(self):
		_customer_a, _customer_b, user_a, job_a, job_b = _make_pair("E1")

		frappe.set_user(user_a.name)
		try:
			result = portal_shipments.get_jobs()
		finally:
			frappe.set_user("Administrator")

		names = [j.name for j in result["jobs"]]
		self.assertIn(job_a.name, names)
		self.assertNotIn(job_b.name, names)

	def test_get_job_detail_allows_own_job(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E2")

		frappe.set_user(user_a.name)
		try:
			result = portal_shipments.get_job_detail(job_a.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["header"]["name"], job_a.name)
		# Financial/margin fields must never appear in a portal response.
		for leaky_key in ("finance", "dnd_totals", "purchase_invoices", "sales_invoices"):
			self.assertNotIn(leaky_key, result)

	def test_get_job_detail_denies_other_customers_job(self):
		_customer_a, _customer_b, user_a, _job_a, job_b = _make_pair("E3")

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_shipments.get_job_detail(job_b.name)
		finally:
			frappe.set_user("Administrator")

	def test_get_overview_scopes_kpis_to_own_customer(self):
		customer_a, _customer_b, user_a, job_a, job_b = _make_pair("E4")
		_make_forwarding_job(customer_a, "E4a2", status="Completed")

		frappe.set_user(user_a.name)
		try:
			result = portal_dashboard.get_overview()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["active_shipments"], 1)  # job_a only; completed one excluded
		recent_names = [j.name for j in result["recent_jobs"]]
		self.assertIn(job_a.name, recent_names)
		self.assertNotIn(job_b.name, recent_names)

	def test_portal_endpoints_reject_guest(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_shipments.get_jobs()
		finally:
			frappe.set_user("Administrator")

	def test_internal_dashboard_still_sees_all_customers_unfiltered(self):
		# Regression guard: Phase 1 must not have touched the internal
		# (Desk-facing) shipment dashboard's own access or data scope.
		_customer_a, _customer_b, _user_a, job_a, job_b = _make_pair("E6")

		frappe.set_user("Administrator")
		result_a = shipment_dashboard.get_jobs(search=job_a.customer_reference[:14])
		self.assertIn(job_a.name, [j.name for j in result_a["jobs"]])

		result_b = shipment_dashboard.get_jobs(search=job_b.customer_reference[:14])
		self.assertIn(job_b.name, [j.name for j in result_b["jobs"]])
