# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Tests for job creation notification email draft builder and send endpoint."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from freightmas.forwarding_service.notifications.job_creation_email import (
	_build_shipment_detail_rows,
	_format_route,
	_format_services_enabled,
	build_job_creation_message,
	build_job_creation_subject,
	get_job_creation_email_draft,
	get_missing_port_clearance_docs,
	render_job_creation_email,
	render_job_creation_email_template,
	send_job_creation_notification,
)
from freightmas.forwarding_service.notifications.job_creation_template_content import (
	FORWARDING_JOB_CREATION_TEMPLATE_HTML,
	FORWARDING_JOB_CREATION_TEMPLATE_NAME,
	FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT,
	JOB_CREATION_TEMPLATE_HTML,
	JOB_CREATION_TEMPLATE_NAME,
	JOB_CREATION_TEMPLATE_SUBJECT,
)


def _enable_job_creation_notifications(enabled=1):
	frappe.db.set_single_value(
		"FreightMas Settings", "enable_job_creation_notifications", enabled
	)


def _set_default_job_creation_template(template_name):
	frappe.db.set_single_value(
		"FreightMas Settings", "default_job_creation_email_template", template_name
	)


def _ensure_job_creation_email_template():
	if frappe.db.exists("Email Template", JOB_CREATION_TEMPLATE_NAME):
		return
	doc = frappe.new_doc("Email Template")
	doc.name = JOB_CREATION_TEMPLATE_NAME
	doc.subject = JOB_CREATION_TEMPLATE_SUBJECT
	doc.use_html = 1
	doc.response_html = JOB_CREATION_TEMPLATE_HTML
	doc.insert(ignore_permissions=True)


def _ensure_forwarding_job_creation_email_template():
	if frappe.db.exists("Email Template", FORWARDING_JOB_CREATION_TEMPLATE_NAME):
		return
	doc = frappe.new_doc("Email Template")
	doc.name = FORWARDING_JOB_CREATION_TEMPLATE_NAME
	doc.subject = FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT
	doc.use_html = 1
	doc.response_html = FORWARDING_JOB_CREATION_TEMPLATE_HTML
	doc.insert(ignore_permissions=True)


def _make_customer(suffix, tracking_email=None):
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"Job Notify Test Customer {suffix}",
			"customer_type": "Company",
			"customer_group": "Commercial",
			"territory": "Zimbabwe",
			"email_id": f"notify.{suffix}@example.com",
		}
	)
	customer.insert(ignore_permissions=True)
	if tracking_email:
		frappe.db.set_value("Customer", customer.name, "tracking_email", tracking_email)
	return customer


def _make_forwarding_job(
	customer,
	suffix,
	requires_port_clearance=0,
	bl_number=None,
	extra_fields=None,
):
	fields = {
		"doctype": "Forwarding Job",
		"company": "Maita",
		"created_by": "Administrator",
		"naming_series": "FWJB-.#####.-.YY.",
		"shipment_mode": "Sea",
		"incoterms": "CIF",
		"direction": "Import",
		"shipment_type": "FCL",
		"customer": customer.name,
		"customer_reference": f"CUST-REF-{suffix}",
		"consignee": customer.name,
		"port_of_loading": "Beira",
		"port_of_discharge": "Durban",
		"destination": "Harare",
		"cargo_count": "1 x 40HC",
		"eta": add_days(nowdate(), 5),
		"status": "Draft",
		"requires_port_clearance": requires_port_clearance,
		"requires_sea_air_freight": 1,
		"is_trucking_required": 1,
		"bl_number": bl_number,
	}
	if extra_fields:
		fields.update(extra_fields)
	job = frappe.get_doc(fields)
	job.insert(ignore_permissions=True)
	return job


class TestJobCreationEmail(IntegrationTestCase):
	def tearDown(self):
		_enable_job_creation_notifications(0)
		_set_default_job_creation_template("")

	def test_get_missing_port_clearance_docs_empty_when_not_required(self):
		customer = _make_customer("nodocs1")
		job = _make_forwarding_job(customer, "nodocs1", requires_port_clearance=0)
		job = frappe.get_doc("Forwarding Job", job.name)
		self.assertEqual(get_missing_port_clearance_docs(job), [])

	def test_get_missing_port_clearance_docs_returns_documentation_stage_only(self):
		customer = _make_customer("docs1")
		job = _make_forwarding_job(customer, "docs1", requires_port_clearance=1)
		job = frappe.get_doc("Forwarding Job", job.name)
		self.assertTrue(job.port_clearance_milestones)

		for row in job.port_clearance_milestones:
			if row.stage == "Documentation":
				row.is_completed = 1
			if row.milestone_label == "Commercial Invoice":
				row.is_completed = 0

		missing = get_missing_port_clearance_docs(job)
		self.assertEqual(missing, ["Commercial Invoice"])
		doc_labels = {
			row.milestone_label
			for row in job.port_clearance_milestones
			if row.stage == "Documentation" and not row.is_completed
		}
		self.assertEqual(set(missing), doc_labels)

	def test_format_route_joins_ports(self):
		customer = _make_customer("route1")
		job = _make_forwarding_job(customer, "route1")
		self.assertEqual(_format_route(job), "Beira → Durban → Harare")

	def test_format_services_enabled_lists_checked_services(self):
		customer = _make_customer("svc1")
		job = _make_forwarding_job(
			customer,
			"svc1",
			extra_fields={
				"requires_sea_air_freight": 1,
				"requires_port_clearance": 1,
				"is_trucking_required": 0,
			},
		)
		self.assertEqual(
			_format_services_enabled(job),
			"Sea/Air Freight, Port Clearance",
		)

	def test_build_shipment_detail_rows_omits_empty_optional_fields(self):
		customer = _make_customer("rows1")
		job = _make_forwarding_job(customer, "rows1")
		job.direction = ""
		job.shipment_mode = ""
		job.shipment_type = ""
		job.port_of_loading = ""
		job.port_of_discharge = ""
		job.destination = ""
		job.eta = None
		job.cargo_count = ""
		job.cargo_description = ""
		job.consignee = ""
		job.requires_sea_air_freight = 0
		job.is_trucking_required = 0
		job.requires_port_clearance = 0
		job.requires_border_clearance = 0
		job.requires_warehousing = 0
		rows = _build_shipment_detail_rows(job)
		labels = [label for label, _value in rows]
		self.assertEqual(labels, ["Job Reference", "BL Number"])

	def test_build_shipment_detail_rows_includes_expanded_fields(self):
		customer = _make_customer("rows2")
		job = _make_forwarding_job(customer, "rows2", bl_number="BL999")
		rows = dict(_build_shipment_detail_rows(job))
		self.assertEqual(rows["Job Reference"], job.name)
		self.assertEqual(rows["BL Number"], "BL999")
		self.assertEqual(rows["Direction"], "Import")
		self.assertEqual(rows["Mode"], "Sea")
		self.assertEqual(rows["Shipment Type"], "FCL")
		self.assertEqual(rows["Route"], "Beira → Durban → Harare")
		self.assertEqual(rows["Cargo"], "1 x 40HC")
		self.assertIn("Sea/Air Freight", rows["Services"])

	def test_build_job_creation_subject(self):
		subject = build_job_creation_subject(
			"FWJB-0146-26", "Grant Plastics", "MEDUL012596"
		)
		self.assertEqual(
			subject,
			"New Shipment - Job: FWJB-0146-26 Grant Plastics MEDUL012596",
		)

	def test_build_job_creation_message_includes_references(self):
		customer = _make_customer("msg1")
		job = _make_forwarding_job(customer, "msg1", bl_number="BL123456")
		message = build_job_creation_message(job, "Acme Ltd", "Maita Logistics", [])
		self.assertIn(job.name, message)
		self.assertIn("Job Reference", message)
		self.assertIn("BL Number", message)
		self.assertIn("BL123456", message)
		self.assertIn("Direction", message)
		self.assertIn("Services", message)
		self.assertIn("Acme Ltd", message)
		self.assertIn("<p", message)
		self.assertNotIn("Your Reference:", message)
		self.assertNotIn("Action required", message)

	def test_build_job_creation_message_shows_dash_when_bl_missing(self):
		customer = _make_customer("msg1b")
		job = _make_forwarding_job(customer, "msg1b")
		message = build_job_creation_message(job, "Acme Ltd", "Maita Logistics", [])
		self.assertIn("BL Number", message)
		self.assertIn("—", message)

	def test_build_job_creation_message_includes_missing_docs_block(self):
		customer = _make_customer("msg2")
		job = _make_forwarding_job(customer, "msg2")
		message = build_job_creation_message(
			job, "Acme Ltd", "Maita Logistics", ["Commercial Invoice", "Bill of Lading"]
		)
		self.assertIn("Action required — documents outstanding", message)
		self.assertIn("Commercial Invoice", message)
		self.assertIn("Bill of Lading", message)
		self.assertIn("#fffbeb", message)

	def test_render_job_creation_email_uses_template(self):
		_ensure_job_creation_email_template()
		customer = _make_customer("tpl1")
		job = _make_forwarding_job(customer, "tpl1", bl_number="BL-TPL")
		rendered = render_job_creation_email(job, template_name=JOB_CREATION_TEMPLATE_NAME)
		self.assertIn(job.name, rendered["subject"])
		self.assertIn(customer.customer_name, rendered["subject"])
		self.assertIn(job.customer_reference, rendered["subject"])
		self.assertIn("SHIPMENT NOTIFICATION", rendered["message"])
		self.assertIn("Shipment Details", rendered["message"])
		self.assertIn("BL-TPL", rendered["message"])
		self.assertIn("Direction", rendered["message"])
		self.assertIn("data-fm-email", rendered["message"])

	def test_render_job_creation_email_template_includes_missing_docs_block(self):
		_ensure_job_creation_email_template()
		customer = _make_customer("tpl2")
		job = _make_forwarding_job(customer, "tpl2", requires_port_clearance=1)
		job = frappe.get_doc("Forwarding Job", job.name)
		for row in job.port_clearance_milestones:
			if row.stage == "Documentation":
				row.is_completed = 0
			if row.milestone_label == "Commercial Invoice":
				row.is_completed = 0

		rendered = render_job_creation_email(job, template_name=JOB_CREATION_TEMPLATE_NAME)
		self.assertIn("Action required — documents outstanding", rendered["message"])
		self.assertIn("Commercial Invoice", rendered["message"])

	def test_render_forwarding_job_creation_email_modern_template(self):
		_ensure_forwarding_job_creation_email_template()
		customer = _make_customer("modern1")
		job = _make_forwarding_job(customer, "modern1", bl_number="BL-MOD")
		rendered = render_job_creation_email(
			job, template_name=FORWARDING_JOB_CREATION_TEMPLATE_NAME
		)
		self.assertIn(job.name, rendered["subject"])
		self.assertIn("Shipment Details", rendered["message"])
		self.assertIn("BL-MOD", rendered["message"])
		self.assertIn("#f8fafc", rendered["message"])
		self.assertIn("Yours faithfully,", rendered["message"])
		self.assertIn("data-fm-email", rendered["message"])

	def test_render_job_creation_email_falls_back_when_template_blank(self):
		customer = _make_customer("fallback1")
		job = _make_forwarding_job(customer, "fallback1")
		rendered = render_job_creation_email(job, template_name="")
		self.assertIn("New Shipment - Job:", rendered["subject"])
		self.assertIn(job.name, rendered["message"])
		self.assertIn("Dear", rendered["message"])

	def test_render_job_creation_email_template_endpoint(self):
		_ensure_job_creation_email_template()
		customer = _make_customer("endpoint1")
		job = _make_forwarding_job(customer, "endpoint1", bl_number="BL-END")
		frappe.set_user("Administrator")
		result = render_job_creation_email_template(job.name, JOB_CREATION_TEMPLATE_NAME)
		self.assertIn(job.name, result["subject"])
		self.assertIn("BL-END", result["message"])

	def test_get_job_creation_email_draft_disabled_when_setting_off(self):
		_enable_job_creation_notifications(0)
		customer = _make_customer("draft1", tracking_email="track@example.com")
		job = _make_forwarding_job(customer, "draft1")
		frappe.set_user("Administrator")
		result = get_job_creation_email_draft(job.name)
		self.assertFalse(result["enabled"])

	def test_get_job_creation_email_draft_returns_prefill(self):
		_enable_job_creation_notifications(1)
		_ensure_job_creation_email_template()
		_set_default_job_creation_template(JOB_CREATION_TEMPLATE_NAME)
		customer = _make_customer("draft2", tracking_email="track@example.com")
		frappe.db.set_value("Customer", customer.name, "tracking_cc_emails", "cc@example.com")
		job = _make_forwarding_job(customer, "draft2", requires_port_clearance=1)
		frappe.set_user("Administrator")
		result = get_job_creation_email_draft(job.name)
		self.assertTrue(result["enabled"])
		self.assertEqual(result["to_email"], "track@example.com")
		self.assertEqual(result["cc_emails"], "cc@example.com")
		self.assertEqual(result["default_email_template"], JOB_CREATION_TEMPLATE_NAME)
		self.assertIn("New Shipment - Job:", result["subject"])
		self.assertIn(job.name, result["subject"])
		self.assertIn(customer.customer_name, result["subject"])
		self.assertIn(job.customer_reference, result["subject"])
		self.assertIn(job.name, result["message"])
		self.assertIn("Shipment Details", result["message"])
		self.assertIn("<p", result["message"])
		self.assertIn("data-fm-email", result["message"])
		self.assertNotIn("Your Reference:", result["message"])

	def test_get_job_creation_email_draft_disabled_when_already_sent(self):
		_enable_job_creation_notifications(1)
		customer = _make_customer("draft3")
		job = _make_forwarding_job(customer, "draft3")
		frappe.db.set_value(
			"Forwarding Job", job.name, "job_creation_notification_sent", 1
		)
		frappe.set_user("Administrator")
		result = get_job_creation_email_draft(job.name)
		self.assertFalse(result["enabled"])

	@patch("freightmas.forwarding_service.notifications.job_creation_email.frappe.sendmail")
	def test_send_job_creation_notification_sets_sent_flag(self, mock_sendmail):
		_enable_job_creation_notifications(1)
		customer = _make_customer("send1", tracking_email="track@example.com")
		job = _make_forwarding_job(customer, "send1")
		frappe.set_user("Administrator")

		result = send_job_creation_notification(
			job.name,
			"track@example.com",
			build_job_creation_subject(job.name, customer.customer_name, job.customer_reference),
			"<p>Test message</p>",
		)
		self.assertTrue(result["success"])
		mock_sendmail.assert_called_once()
		self.assertEqual(
			frappe.db.get_value("Forwarding Job", job.name, "job_creation_notification_sent"),
			1,
		)

	@patch("freightmas.forwarding_service.notifications.job_creation_email.frappe.sendmail")
	def test_send_job_creation_notification_blocks_second_send(self, mock_sendmail):
		_enable_job_creation_notifications(1)
		customer = _make_customer("send2", tracking_email="track@example.com")
		job = _make_forwarding_job(customer, "send2")
		frappe.set_user("Administrator")

		send_job_creation_notification(
			job.name,
			"track@example.com",
			build_job_creation_subject(job.name, customer.customer_name, job.customer_reference),
			"<p>Test message</p>",
		)
		with self.assertRaises(frappe.ValidationError):
			send_job_creation_notification(
				job.name,
				"track@example.com",
				build_job_creation_subject(job.name, customer.customer_name, job.customer_reference),
				"<p>Test message again</p>",
			)
		self.assertEqual(mock_sendmail.call_count, 1)
