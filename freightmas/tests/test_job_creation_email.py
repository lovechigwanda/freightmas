# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Tests for job creation notification email draft builder and send endpoint."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from freightmas.forwarding_service.notifications.job_creation_email import (
	build_job_creation_message,
	get_job_creation_email_draft,
	get_missing_port_clearance_docs,
	send_job_creation_notification,
)


def _enable_job_creation_notifications(enabled=1):
	frappe.db.set_single_value(
		"FreightMas Settings", "enable_job_creation_notifications", enabled
	)


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


def _make_forwarding_job(customer, suffix, requires_port_clearance=0):
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
			"customer_reference": f"CUST-REF-{suffix}",
			"consignee": customer.name,
			"port_of_loading": "Beira",
			"port_of_discharge": "Harare",
			"destination": "Harare",
			"eta": add_days(nowdate(), 5),
			"status": "Draft",
			"requires_port_clearance": requires_port_clearance,
		}
	)
	job.insert(ignore_permissions=True)
	return job


class TestJobCreationEmail(IntegrationTestCase):
	def tearDown(self):
		_enable_job_creation_notifications(0)

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

	def test_build_job_creation_message_includes_references(self):
		customer = _make_customer("msg1")
		job = _make_forwarding_job(customer, "msg1")
		message = build_job_creation_message(job, "Acme Ltd", "Maita Logistics", [])
		self.assertIn(job.name, message)
		self.assertIn(job.customer_reference, message)
		self.assertIn("Acme Ltd", message)
		self.assertNotIn("Action required", message)

	def test_build_job_creation_message_includes_missing_docs_block(self):
		customer = _make_customer("msg2")
		job = _make_forwarding_job(customer, "msg2")
		message = build_job_creation_message(
			job, "Acme Ltd", "Maita Logistics", ["Commercial Invoice", "Bill of Lading"]
		)
		self.assertIn("Action required", message)
		self.assertIn("Commercial Invoice", message)
		self.assertIn("Bill of Lading", message)

	def test_get_job_creation_email_draft_disabled_when_setting_off(self):
		_enable_job_creation_notifications(0)
		customer = _make_customer("draft1", tracking_email="track@example.com")
		job = _make_forwarding_job(customer, "draft1")
		frappe.set_user("Administrator")
		result = get_job_creation_email_draft(job.name)
		self.assertFalse(result["enabled"])

	def test_get_job_creation_email_draft_returns_prefill(self):
		_enable_job_creation_notifications(1)
		customer = _make_customer("draft2", tracking_email="track@example.com")
		frappe.db.set_value("Customer", customer.name, "tracking_cc_emails", "cc@example.com")
		job = _make_forwarding_job(customer, "draft2", requires_port_clearance=1)
		frappe.set_user("Administrator")
		result = get_job_creation_email_draft(job.name)
		self.assertTrue(result["enabled"])
		self.assertEqual(result["to_email"], "track@example.com")
		self.assertEqual(result["cc_emails"], "cc@example.com")
		self.assertIn(job.name, result["subject"])
		self.assertIn(job.name, result["message"])
		self.assertIn(job.customer_reference, result["message"])

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
			f"Shipment Registered - {job.name}",
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
			f"Shipment Registered - {job.name}",
			"<p>Test message</p>",
		)
		with self.assertRaises(frappe.ValidationError):
			send_job_creation_notification(
				job.name,
				"track@example.com",
				f"Shipment Registered - {job.name}",
				"<p>Test message again</p>",
			)
		self.assertEqual(mock_sendmail.call_count, 1)
