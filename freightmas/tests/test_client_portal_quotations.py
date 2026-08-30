# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Cross-tenant tests for the Client Portal quotations API.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from freightmas.portal.api import dashboard as portal_dashboard
from freightmas.portal.api import quotations as portal_quotations

QUOTE_COMPANY = "Maita (Demo)"
QUOTE_ITEM = "SKU008"


def _make_customer(suffix):
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"Portal Quotes Test Customer {suffix}",
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
			"email": f"portal.quotes.{suffix}@example.com",
			"first_name": f"Portal Quotes {suffix}",
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


def _make_quotation(customer, suffix, workflow_state="Sent to Customer", valid_days=30):
	initial_valid_till = add_days(nowdate(), max(valid_days, 1))
	qtn = frappe.get_doc(
		{
			"doctype": "Quotation",
			"company": QUOTE_COMPANY,
			"quotation_to": "Customer",
			"party_name": customer.name,
			"transaction_date": nowdate(),
			"valid_till": initial_valid_till,
			"job_type": "Forwarding",
			"is_freight_quote": 1,
			"customer_reference": f"REF-{suffix}",
			"items": [
				{
					"item_code": QUOTE_ITEM,
					"qty": 1,
					"rate": 250,
				}
			],
		}
	)
	qtn.insert(ignore_permissions=True)
	qtn.submit()
	if valid_days < 0:
		frappe.db.set_value("Quotation", qtn.name, "valid_till", add_days(nowdate(), valid_days))
		qtn.reload()
	frappe.db.set_value("Quotation", qtn.name, "workflow_state", workflow_state)
	qtn.reload()
	return qtn


def _make_job_order(customer, quotation, suffix):
	jo = frappe.get_doc(
		{
			"doctype": "Job Order",
			"company": QUOTE_COMPANY,
			"naming_series": "FWJO-.#####.-.YY",
			"quotation_reference": quotation.name,
			"customer": customer.name,
			"customer_reference": f"PO-QUOTE-{suffix}",
			"order_date": nowdate(),
			"prepared_by": "Administrator",
			"service_type": "Forwarding",
		}
	)
	jo.insert(ignore_permissions=True)
	return jo


def _make_forwarding_job(customer, suffix, job_order=None):
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
			"customer_reference": f"PO-PORTAL-QUOTE-{suffix}",
			"consignee": customer.name,
			"port_of_loading": "Beira",
			"port_of_discharge": "Harare",
			"destination": "Harare",
			"eta": add_days(nowdate(), 5),
			"status": "Draft",
		}
	)
	if job_order:
		job.job_order_reference = job_order.name
	job.insert(ignore_permissions=True)
	if job_order:
		frappe.db.set_value("Job Order", job_order.name, "forwarding_job_reference", job.name)
	return job


def _make_pair(suffix, **quote_kwargs):
	customer_a = _make_customer(f"{suffix}a")
	customer_b = _make_customer(f"{suffix}b")
	user_a = _make_user_and_contact(f"{suffix}a", customer_a)
	quote_a = _make_quotation(customer_a, f"{suffix}a", **quote_kwargs)
	quote_b = _make_quotation(customer_b, f"{suffix}b", **quote_kwargs)
	return customer_a, customer_b, user_a, quote_a, quote_b


class TestPortalQuotationsCrossTenant(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_get_quotations_returns_only_own_customer_pending_quotes(self):
		_customer_a, _customer_b, user_a, quote_a, quote_b = _make_pair("Q1")

		frappe.set_user(user_a.name)
		try:
			result = portal_quotations.get_quotations(status="pending")
		finally:
			frappe.set_user("Administrator")

		names = [row["name"] for row in result["quotations"]]
		self.assertIn(quote_a.name, names)
		self.assertNotIn(quote_b.name, names)

	def test_get_quotation_detail_denies_other_customers_quote(self):
		_customer_a, _customer_b, user_a, _quote_a, quote_b = _make_pair("Q2")

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_quotations.get_quotation_detail(quote_b.name)
		finally:
			frappe.set_user("Administrator")

	def test_approve_quotation_transitions_to_accepted(self):
		customer_a = _make_customer("Q3a")
		user_a = _make_user_and_contact("Q3a", customer_a)
		quote_a = _make_quotation(customer_a, "Q3a")

		frappe.set_user(user_a.name)
		try:
			result = portal_quotations.approve_quotation(quote_a.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["workflow_state"], "Accepted")
		self.assertEqual(frappe.db.get_value("Quotation", quote_a.name, "workflow_state"), "Accepted")

	def test_reject_quotation_transitions_to_rejected(self):
		customer_a = _make_customer("Q4a")
		user_a = _make_user_and_contact("Q4a", customer_a)
		quote_a = _make_quotation(customer_a, "Q4a")

		frappe.set_user(user_a.name)
		try:
			result = portal_quotations.reject_quotation(quote_a.name, reason="Price too high")
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["workflow_state"], "Rejected")
		self.assertEqual(frappe.db.get_value("Quotation", quote_a.name, "workflow_state"), "Rejected")

	def test_approve_quotation_blocks_expired_quote(self):
		customer_a = _make_customer("Q5a")
		user_a = _make_user_and_contact("Q5a", customer_a)
		quote_a = _make_quotation(customer_a, "Q5a", valid_days=-1)

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.ValidationError):
				portal_quotations.approve_quotation(quote_a.name)
		finally:
			frappe.set_user("Administrator")

	def test_get_job_quotations_returns_linked_accepted_quote(self):
		customer_a = _make_customer("Q6a")
		user_a = _make_user_and_contact("Q6a", customer_a)
		quote_a = _make_quotation(customer_a, "Q6a", workflow_state="Accepted")
		job_order = _make_job_order(customer_a, quote_a, "Q6")
		job_a = _make_forwarding_job(customer_a, "Q6", job_order=job_order)

		frappe.set_user(user_a.name)
		try:
			result = portal_quotations.get_job_quotations(job_a.name)
		finally:
			frappe.set_user("Administrator")

		names = [row["name"] for row in result["quotations"]]
		self.assertEqual(names, [quote_a.name])

	def test_get_job_quotations_empty_without_job_order_chain(self):
		customer_a = _make_customer("Q7a")
		user_a = _make_user_and_contact("Q7a", customer_a)
		job_a = _make_forwarding_job(customer_a, "Q7")

		frappe.set_user(user_a.name)
		try:
			result = portal_quotations.get_job_quotations(job_a.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["quotations"], [])

	def test_download_quotation_pdf_denies_other_customer(self):
		_customer_a, _customer_b, user_a, _quote_a, quote_b = _make_pair("Q8")

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_quotations.download_quotation_pdf(quote_b.name)
		finally:
			frappe.set_user("Administrator")

	def test_download_quotation_pdf_sets_download_disposition(self):
		_customer_a, _customer_b, user_a, quote_a, _quote_b = _make_pair("Q8b")

		frappe.set_user(user_a.name)
		try:
			portal_quotations.download_quotation_pdf(quote_a.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(frappe.local.response.type, "download")
		self.assertTrue(frappe.local.response.filename.endswith(".pdf"))
		self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))

	def test_get_overview_includes_pending_quotation_attention(self):
		customer_a = _make_customer("Q9a")
		user_a = _make_user_and_contact("Q9a", customer_a)
		quote_a = _make_quotation(customer_a, "Q9a")

		frappe.set_user(user_a.name)
		try:
			result = portal_dashboard.get_overview()
		finally:
			frappe.set_user("Administrator")

		self.assertGreaterEqual(result["pending_quotation_count"], 1)
		types = [item["type"] for item in result["attention_items"]]
		self.assertIn("pending_quotation", types)
		pending = next(item for item in result["attention_items"] if item["type"] == "pending_quotation")
		self.assertEqual(pending["quotation_name"], quote_a.name)

	def test_portal_endpoints_reject_guest(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_quotations.get_quotations()
		finally:
			frappe.set_user("Administrator")

	def test_get_quotations_approved_excludes_job_created(self):
		customer_a = _make_customer("Q10a")
		user_a = _make_user_and_contact("Q10a", customer_a)
		accepted = _make_quotation(customer_a, "Q10a", workflow_state="Accepted")
		job_created = _make_quotation(customer_a, "Q10b", workflow_state="JO Created")

		frappe.set_user(user_a.name)
		try:
			result = portal_quotations.get_quotations(status="approved")
		finally:
			frappe.set_user("Administrator")

		names = [row["name"] for row in result["quotations"]]
		self.assertIn(accepted.name, names)
		self.assertNotIn(job_created.name, names)

	def test_get_quotations_job_created_returns_only_jo_created(self):
		customer_a = _make_customer("Q11a")
		user_a = _make_user_and_contact("Q11a", customer_a)
		accepted = _make_quotation(customer_a, "Q11a", workflow_state="Accepted")
		job_created = _make_quotation(customer_a, "Q11b", workflow_state="JO Created")

		frappe.set_user(user_a.name)
		try:
			result = portal_quotations.get_quotations(status="job_created")
		finally:
			frappe.set_user("Administrator")

		names = [row["name"] for row in result["quotations"]]
		self.assertIn(job_created.name, names)
		self.assertNotIn(accepted.name, names)
		self.assertEqual(result["quotations"][0]["client_status"], "Job created")

	def test_cancelled_quotation_excluded_from_all_tabs(self):
		customer_a = _make_customer("Q12a")
		user_a = _make_user_and_contact("Q12a", customer_a)
		cancelled = _make_quotation(customer_a, "Q12a", workflow_state="Cancelled")

		frappe.set_user(user_a.name)
		try:
			for status in ("pending", "approved", "job_created", "declined"):
				result = portal_quotations.get_quotations(status=status)
				names = [row["name"] for row in result["quotations"]]
				self.assertNotIn(
					cancelled.name,
					names,
					msg=f"Cancelled quotation should not appear in {status} tab",
				)
		finally:
			frappe.set_user("Administrator")
