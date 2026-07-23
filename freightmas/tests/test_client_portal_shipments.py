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

import io

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, formatdate, nowdate
from openpyxl import load_workbook

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


def _add_container(job, suffix, container_type="20SD", **milestone_kwargs):
	"""Append a Cargo Parcel Details row and set its trucking-milestone
	booleans/dates directly at the DB level, bypassing the controller's
	milestone-sequence validation (same technique _make_forwarding_job uses
	for status) since these read-path tests don't care about that business
	rule.

	Reloads from the DB first rather than trusting the caller's `job`
	reference is still current - callers append multiple containers across
	several calls and a stale in-memory `modified` timestamp trips
	TimestampMismatchError on save.
	"""
	job = frappe.get_doc("Forwarding Job", job.name)
	job.append("cargo_parcel_details", {
		"cargo_type": "Containerised",
		"container_number": f"CONT-{suffix}",
		"container_type": container_type,
		"cargo_quantity": 1,
	})
	job.save(ignore_permissions=True)
	row = job.cargo_parcel_details[-1]
	if milestone_kwargs:
		frappe.db.set_value("Cargo Parcel Details", row.name, milestone_kwargs)
	job.reload()
	return job


def _complete_milestone(job, fieldname, completed_on=None):
	"""Mark the first row of a Job Milestone Progress checklist as completed,
	directly at the DB level."""
	rows = job.get(fieldname) or []
	if not rows:
		return
	frappe.db.set_value(
		"Job Milestone Progress",
		rows[0].name,
		{"is_completed": 1, "completed_on": completed_on or nowdate()},
	)


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

	def _export_as_user(self, user, **kwargs):
		"""Runs export_tracking_report and parses the resulting single-table
		workbook: one header row, then a bold "job" row per Forwarding Job
		followed immediately by its (collapsible, outline_level=1) container
		rows. A row is classified as a job row if any of the job-only columns
		(here: Consignee) is populated, container row otherwise."""
		frappe.set_user(user.name)
		try:
			portal_shipments.export_tracking_report(**kwargs)
		finally:
			frappe.set_user("Administrator")
		wb = load_workbook(io.BytesIO(frappe.local.response.filecontent))
		ws = wb.active
		rows = list(ws.iter_rows(values_only=True))

		header = rows[0]
		consignee_col = header.index("Consignee")
		container_number_col = header.index("Container Number")

		job_rows = []
		container_rows = []
		for row_idx, row in enumerate(rows[1:], 2):
			if row[consignee_col] is not None:
				job_rows.append(row)
				self.assertEqual(ws.row_dimensions[row_idx].outline_level, 0)
			else:
				container_rows.append(row)
				self.assertEqual(ws.row_dimensions[row_idx].outline_level, 1)

		self.assertFalse(ws.sheet_properties.outlinePr.summaryBelow)

		return {
			"header": header,
			"job_rows": job_rows,
			"container_rows": container_rows,
			"container_number_col": container_number_col,
		}

	def test_export_tracking_report_scopes_to_own_customer(self):
		customer_a, _customer_b, user_a, job_a, job_b = _make_pair("E7")

		result = self._export_as_user(user_a)

		self.assertEqual(result["header"][0], "Job ID")
		job_ids = {r[0] for r in result["job_rows"]}
		self.assertIn(job_a.name, job_ids)
		self.assertNotIn(job_b.name, job_ids)

	def test_export_tracking_report_one_row_per_container(self):
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E8")
		_add_container(job_a, "E8-1", is_booked=1, booked_on_date=nowdate())
		_add_container(job_a, "E8-2", is_booked=1, is_loaded=1, loaded_on_date=nowdate())

		result = self._export_as_user(user_a)

		# Exactly one job row for the job - no BL-level repetition.
		job_job_rows = [r for r in result["job_rows"] if r[0] == job_a.name]
		self.assertEqual(len(job_job_rows), 1)

		# Two container rows, one per container, grouped under the job row.
		container_job_rows = [r for r in result["container_rows"] if r[0] == job_a.name]
		self.assertEqual(len(container_job_rows), 2)

		trucking_col = result["header"].index("Trucking Milestones")
		stages = {r[trucking_col] for r in container_job_rows}
		self.assertEqual(
			stages,
			{f"Booked ({formatdate(nowdate(), 'dd-MMM-yy')})", f"Loaded ({formatdate(nowdate(), 'dd-MMM-yy')})"},
		)

	def test_export_tracking_report_job_with_no_containers_still_appears(self):
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E9")

		result = self._export_as_user(user_a)

		job_job_rows = [r for r in result["job_rows"] if r[0] == job_a.name]
		self.assertEqual(len(job_job_rows), 1)

		container_job_rows = [r for r in result["container_rows"] if r[0] == job_a.name]
		self.assertEqual(container_job_rows, [])

	def test_export_tracking_report_job_level_milestones_shown_once(self):
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E10")

		# Port Clearance checklist only auto-populates via populate_mode_
		# milestones() on validate/save, once requires_port_clearance is set.
		frappe.db.set_value("Forwarding Job", job_a.name, "requires_port_clearance", 1)
		job_a.reload()
		job_a.save(ignore_permissions=True)
		job_a.reload()
		_complete_milestone(job_a, "port_clearance_milestones", completed_on=nowdate())
		_add_container(job_a, "E10-1")
		_add_container(job_a, "E10-2")

		result = self._export_as_user(user_a)

		job_job_rows = [r for r in result["job_rows"] if r[0] == job_a.name]
		self.assertEqual(len(job_job_rows), 1)  # single source of truth, no per-container repeat

		port_col = result["header"].index("Port Clearance Milestones")
		self.assertNotEqual(job_job_rows[0][port_col], "")

		# Container rows for this job leave the Port Clearance column blank -
		# it's a job-level column, not written on container-level rows.
		container_job_rows = [r for r in result["container_rows"] if r[0] == job_a.name]
		for r in container_job_rows:
			self.assertIsNone(r[port_col])

	def test_export_tracking_report_reflects_status_filter(self):
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E11")
		_make_forwarding_job(customer_a, "E11a2", status="Completed")

		result = self._export_as_user(user_a, status="Completed")
		job_ids = {r[0] for r in result["job_rows"]}
		self.assertNotIn(job_a.name, job_ids)  # job_a is "In Progress", filtered out
