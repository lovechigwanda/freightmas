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
		"""Runs export_tracking_report and parses the resulting workbook: a
		single "Tracking Report" sheet with row 1 = main title, row 2 =
		section band headers, row 3 = column headers, row 4+ = one data row
		per container (or one row per containerless job)."""
		frappe.set_user(user.name)
		try:
			portal_shipments.export_tracking_report(**kwargs)
		finally:
			frappe.set_user("Administrator")
		wb = load_workbook(io.BytesIO(frappe.local.response.filecontent))
		self.assertEqual(wb.sheetnames, ["Tracking Report"])

		ws = wb["Tracking Report"]
		rows = list(ws.iter_rows(values_only=True))
		self.assertEqual(rows[0][0], "Shipment Tracking Report")
		header = rows[2]
		data_rows = [r for r in rows[3:] if r[0] is not None]
		return header, data_rows

	def test_export_tracking_report_scopes_to_own_customer(self):
		customer_a, _customer_b, user_a, job_a, job_b = _make_pair("E7")

		header, data_rows = self._export_as_user(user_a)

		self.assertEqual(header[0], "Job ID")
		job_ids = {r[0] for r in data_rows}
		self.assertIn(job_a.name, job_ids)
		self.assertNotIn(job_b.name, job_ids)

	def test_export_tracking_report_one_row_per_container(self):
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E8")
		_add_container(job_a, "E8-1", booked_on_date=nowdate())
		_add_container(job_a, "E8-2", booked_on_date=nowdate(), loaded_on_date=nowdate())

		header, data_rows = self._export_as_user(user_a)

		job_rows = [r for r in data_rows if r[0] == job_a.name]
		self.assertEqual(len(job_rows), 2)  # one row per container

		booked_col = header.index("Booked")
		loaded_col = header.index("Loaded")
		booked_dates = {r[booked_col] for r in job_rows}
		loaded_values = {r[loaded_col] for r in job_rows}
		self.assertEqual(booked_dates, {formatdate(nowdate(), "dd-MMM-yy")})  # both containers booked
		# openpyxl round-trips a blank cell (we write "") back as None, not "".
		self.assertEqual(loaded_values, {None, formatdate(nowdate(), "dd-MMM-yy")})  # only one loaded

		# Job/BL-level identity fields repeat identically on both container rows.
		consignee_col = header.index("Consignee")
		self.assertEqual({r[consignee_col] for r in job_rows}, {customer_a.customer_name})

	def test_export_tracking_report_job_with_no_containers_gets_one_row(self):
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E9")

		header, data_rows = self._export_as_user(user_a)

		job_rows = [r for r in data_rows if r[0] == job_a.name]
		self.assertEqual(len(job_rows), 1)

		booked_col = header.index("Booked")
		container_number_col = header.index("Container Number")
		self.assertIsNone(job_rows[0][booked_col])
		self.assertIsNone(job_rows[0][container_number_col])

	def test_export_tracking_report_job_level_milestones_repeat_across_containers(self):
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

		header, data_rows = self._export_as_user(user_a)
		job_rows = [r for r in data_rows if r[0] == job_a.name]
		self.assertEqual(len(job_rows), 2)

		# The completed milestone's own column (its label, from Milestone
		# Definition) shows the same date on every container row of this job.
		completed_code = job_a.port_clearance_milestones[0].milestone_code
		completed_label = job_a.port_clearance_milestones[0].milestone_label
		port_col = header.index(completed_label)
		self.assertEqual(
			{r[port_col] for r in job_rows},
			{formatdate(nowdate(), "dd-MMM-yy")},
		)

	def test_export_tracking_report_percent_complete_ignores_inapplicable_milestones(self):
		# A job with neither optional section (Port/Border Clearance)
		# required has a denominator of exactly 6 (Sea/Air) + 5 (Road
		# Transport) + 1 (Overview Completed) = 12 - the Port/Border
		# Clearance milestone columns in the sheet must not count against it
		# just because those columns exist for other jobs.
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E12")
		frappe.db.set_value("Forwarding Job", job_a.name, "atd", nowdate())

		header, data_rows = self._export_as_user(user_a)
		job_rows = [r for r in data_rows if r[0] == job_a.name]
		self.assertEqual(len(job_rows), 1)

		percent_col = header.index("% Complete")
		# 2/12: ATD (just set) and ETA/ATA (the fixture's own `eta` falls back
		# into this column) - everything else, including all Port/Border
		# Clearance columns, stays outstanding.
		self.assertAlmostEqual(job_rows[0][percent_col], 2 / 12, places=4)

	def test_export_tracking_report_shows_dash_for_not_required_service(self):
		# A job with requires_border_clearance=1 but requires_port_clearance
		# unset (the default): every Port Clearance column shows "-" (not a
		# blank/amber "outstanding" cell), and Port Clearance contributes
		# nothing to % Complete - only Border Clearance's own 5 milestones do.
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E13")
		frappe.db.set_value("Forwarding Job", job_a.name, "requires_border_clearance", 1)
		job_a.reload()
		job_a.save(ignore_permissions=True)
		job_a.reload()
		self.assertTrue(job_a.border_clearance_milestones)  # checklist populated
		_complete_milestone(job_a, "border_clearance_milestones", completed_on=nowdate())

		header, data_rows = self._export_as_user(user_a)
		job_rows = [r for r in data_rows if r[0] == job_a.name]
		self.assertEqual(len(job_rows), 1)

		# Every Port Clearance column (identified by falling between the
		# Sea/Air and Road Transport sections in the header) shows "-".
		port_clearance_cols = range(header.index("Empty Returned") + 1, header.index("Booked"))
		self.assertTrue(port_clearance_cols)  # sanity: the system has some Port Clearance definitions
		for col in port_clearance_cols:
			self.assertEqual(job_rows[0][col], "-")

		completed_label = job_a.border_clearance_milestones[0].milestone_label
		border_col = header.index(completed_label)
		self.assertEqual(job_rows[0][border_col], formatdate(nowdate(), "dd-MMM-yy"))

		percent_col = header.index("% Complete")
		# 2 completed (ETA/ATA - the fixture's own `eta` falls back into this
		# column - and the Border Clearance milestone) / (12 base + 5 Border
		# Clearance applicable) = 2/17 - Port Clearance's columns (shown as
		# "-") aren't in the denominator at all.
		self.assertAlmostEqual(job_rows[0][percent_col], 2 / 17, places=4)

	def test_export_tracking_report_reflects_status_filter(self):
		customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("E11")
		_make_forwarding_job(customer_a, "E11a2", status="Completed")

		_header, data_rows = self._export_as_user(user_a, status="Completed")
		job_ids = {r[0] for r in data_rows}
		self.assertNotIn(job_a.name, job_ids)  # job_a is "In Progress", filtered out
