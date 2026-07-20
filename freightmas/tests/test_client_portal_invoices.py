# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Phase 2 cross-tenant tests for the Client Portal invoices/billing API.

Mirrors the structure of test_client_portal_shipments.py: two customers,
one Sales Invoice each, one provisioned portal user for customer A - every
endpoint must return customer A's own data and reject any attempt to read
customer B's.

Most Sales Invoices are left as Draft (docstatus=0): freightmas.portal.api.
invoices.get_invoices()/get_invoice_detail() filter on `docstatus < 2`
(mirroring the Purchase Invoice pattern in freightmas.portal.supplier.
invoices) so Draft already satisfies it, and ERPNext's calculate_taxes_and_
totals() populates grand_total/outstanding_amount during validate()
regardless of docstatus - submitting buys nothing for those read-path
scoping tests. Same fixture-simplification trick the shipments suite uses
for Forwarding Job status.

The billing-KPI endpoints (get_invoices_summary, dashboard.get_overview)
deliberately filter on `docstatus = 1` only - a Draft invoice isn't real
money owed yet - so their tests submit real invoices instead.

Each test builds its own fixtures with a suffix unique to that test method
(rather than sharing a setUp()) - see that file's docstring for why.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from freightmas.portal.api import dashboard as portal_dashboard
from freightmas.portal.api import invoices as portal_invoices

INVOICE_COMPANY = "Maita (Demo)"
INVOICE_ITEM = "SKU008"
INVOICE_INCOME_ACCOUNT = "Sales - MD"
INVOICE_COST_CENTER = "Main - MD"


def _make_customer(suffix):
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"Portal Invoices Test Customer {suffix}",
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
			"email": f"portal.inv.{suffix}@example.com",
			"first_name": f"Portal Invoices {suffix}",
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


def _make_forwarding_job(customer, suffix):
	# forwarding_job_reference is a Link field to Forwarding Job - a fake
	# non-existent name fails Frappe's own link validation on insert, so
	# the job referenced from an invoice fixture must actually exist.
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
			"customer_reference": f"PO-PORTAL-INV-TEST-{suffix}",
			"consignee": customer.name,
			"port_of_loading": "Beira",
			"port_of_discharge": "Harare",
			"destination": "Harare",
			"eta": add_days(nowdate(), 5),
			"status": "Draft",
		}
	)
	job.insert(ignore_permissions=True)
	return job


def _make_sales_invoice(customer, suffix, days_ago_due=-30, job_reference=None, submit=False):
	# ERPNext's own validate_due_date() rejects a due_date before posting_date,
	# so an "overdue" fixture (due_date in the past) must also back-date
	# posting_date to match - the overdue query only cares that due_date is
	# before today, not where posting_date sits relative to it.
	due_date = add_days(nowdate(), days_ago_due)
	posting_date = due_date if getdate(due_date) < getdate(nowdate()) else nowdate()
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": INVOICE_COMPANY,
			"customer": customer.name,
			"posting_date": posting_date,
			# Without this, ERPNext's validate_posting_time() silently
			# overwrites posting_date back to today, breaking the
			# back-dated-invoice fixtures above.
			"set_posting_time": 1,
			"due_date": due_date,
			"items": [
				{
					"item_code": INVOICE_ITEM,
					"qty": 1,
					"rate": 100,
					"income_account": INVOICE_INCOME_ACCOUNT,
					"cost_center": INVOICE_COST_CENTER,
				}
			],
		}
	)
	if job_reference:
		si.is_forwarding_invoice = 1
		si.forwarding_job_reference = job_reference
	si.insert(ignore_permissions=True)
	if submit:
		si.submit()
	return si


def _make_pair(suffix, **invoice_kwargs):
	"""Two customers + one Sales Invoice each + one portal user for A."""
	customer_a = _make_customer(f"{suffix}a")
	customer_b = _make_customer(f"{suffix}b")
	user_a = _make_user_and_contact(f"{suffix}a", customer_a)
	invoice_a = _make_sales_invoice(customer_a, f"{suffix}a", **invoice_kwargs)
	invoice_b = _make_sales_invoice(customer_b, f"{suffix}b", **invoice_kwargs)
	return customer_a, customer_b, user_a, invoice_a, invoice_b


class TestPortalInvoicesCrossTenant(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_get_invoices_returns_only_own_customer_invoices(self):
		_customer_a, _customer_b, user_a, invoice_a, invoice_b = _make_pair("I1")

		frappe.set_user(user_a.name)
		try:
			result = portal_invoices.get_invoices()
		finally:
			frappe.set_user("Administrator")

		names = [i["name"] for i in result["invoices"]]
		self.assertIn(invoice_a.name, names)
		self.assertNotIn(invoice_b.name, names)

	def test_get_invoice_detail_allows_own_invoice_and_resolves_job_reference(self):
		customer_a = _make_customer("I2a")
		user_a = _make_user_and_contact("I2a", customer_a)
		job_a = _make_forwarding_job(customer_a, "I2")
		invoice_a = _make_sales_invoice(customer_a, "I2a", job_reference=job_a.name)

		frappe.set_user(user_a.name)
		try:
			result = portal_invoices.get_invoice_detail(invoice_a.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["name"], invoice_a.name)
		self.assertEqual(result["job_doctype"], "Forwarding Job")
		self.assertEqual(result["job_name"], job_a.name)
		self.assertIn("payment_history", result)
		self.assertEqual(result["payment_history"], [])

	def test_get_invoice_detail_denies_other_customers_invoice(self):
		_customer_a, _customer_b, user_a, _invoice_a, invoice_b = _make_pair("I3")

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_invoices.get_invoice_detail(invoice_b.name)
		finally:
			frappe.set_user("Administrator")

	def test_download_invoice_pdf_denies_other_customers_invoice(self):
		_customer_a, _customer_b, user_a, _invoice_a, invoice_b = _make_pair("I4")

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_invoices.download_invoice_pdf(invoice_b.name)
		finally:
			frappe.set_user("Administrator")

	def test_get_invoices_summary_scopes_outstanding_and_overdue_to_own_customer(self):
		customer_a, _customer_b, user_a, invoice_a, _invoice_b = _make_pair(
			"I5", days_ago_due=-10, submit=True
		)

		frappe.set_user(user_a.name)
		try:
			result = portal_invoices.get_invoices_summary()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["outstanding_amount"], invoice_a.grand_total)
		self.assertEqual(result["overdue_amount"], invoice_a.grand_total)  # due_date is in the past

	def test_get_overview_includes_outstanding_scoped_to_own_customer(self):
		_customer_a, _customer_b, user_a, invoice_a, invoice_b = _make_pair(
			"I6", days_ago_due=5, submit=True
		)

		frappe.set_user(user_a.name)
		try:
			result = portal_dashboard.get_overview()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["outstanding_amount"], invoice_a.grand_total)
		self.assertEqual(result["overdue_amount"], 0)  # due_date is 5 days in the future

	def test_portal_endpoints_reject_guest(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_invoices.get_invoices()
		finally:
			frappe.set_user("Administrator")
