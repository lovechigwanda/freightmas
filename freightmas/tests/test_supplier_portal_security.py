# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Phase 0/1 tests for the Supplier Portal security foundation.

Mirrors test_client_portal_security.py's categories, adapted for Supplier:
provisioning (plus a new dual-role case with no Customer precedent - a
Contact linked to both a Customer and a Supplier), check_portal_access
generalized with a role= parameter (with a regression guard proving the
Customer-portal default behaviour is unchanged), assert_supplier_scope, and
the child-row charge-line scoping in freightmas.portal.supplier_scope,
which has no Customer-side analog at all since a Customer owns a whole Job
via one parent field while a Supplier's relationship lives in per-line
child tables that can carry several different suppliers' rows on the same
Job.

Uses frappe.tests.IntegrationTestCase so every test runs inside a rolled-
back savepoint.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from freightmas.portal.security import (
	CUSTOMER_PORTAL_ROLE,
	SUPPLIER_PORTAL_ROLE,
	assert_supplier_scope,
	check_portal_access,
	get_portal_customer_names,
	get_portal_supplier_names,
)
from freightmas.portal.supplier_scope import get_supplier_scoped_charges


def _make_customer(suffix):
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"Supplier Portal Test Customer {suffix}",
			"customer_type": "Company",
			"customer_group": "Commercial",
			"territory": "Zimbabwe",
		}
	)
	customer.insert(ignore_permissions=True)
	return customer


def _make_supplier(suffix):
	supplier = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": f"Supplier Portal Test Supplier {suffix}",
			"supplier_type": "Company",
		}
	)
	supplier.insert(ignore_permissions=True)
	return supplier


def _make_user(suffix, roles=None):
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": f"supplier.portal.test.{suffix}@example.com",
			"first_name": f"Supplier Portal Test {suffix}",
			"send_welcome_email": 0,
		}
	)
	for role in roles or []:
		user.append("roles", {"role": role})
	user.insert(ignore_permissions=True)
	return user


def _make_contact(user, suppliers=None, customers=None):
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": user.first_name,
			"user": user.name,
			"email_ids": [{"email_id": user.email, "is_primary": 1}],
		}
	)
	for supplier in suppliers or []:
		contact.append("links", {"link_doctype": "Supplier", "link_name": supplier.name})
	for customer in customers or []:
		contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	contact.insert(ignore_permissions=True)
	return contact


def _make_forwarding_job_with_charges(customer, suffix, charge_rows):
	"""A Forwarding Job with cost/costing charge rows, one per (supplier, buy_rate)
	pair in charge_rows - used to exercise the child-row scoping logic that has
	no Customer-portal precedent."""
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
			"customer_reference": f"PO-SUPPLIER-TEST-{suffix}",
			"consignee": customer.name,
			"port_of_loading": "Beira",
			"port_of_discharge": "Harare",
			"destination": "Harare",
			"eta": add_days(nowdate(), 5),
			"status": "Draft",
		}
	)
	for supplier, buy_rate in charge_rows:
		job.append(
			"forwarding_cost_charges",
			{"charge": "Ocean Freight", "qty": 1, "buy_rate": buy_rate, "supplier": supplier.name},
		)
	job.flags.ignore_validate = True
	job.insert(ignore_permissions=True)
	return job


class TestSupplierPortalProvisioning(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_contact_with_supplier_link_forces_website_user_and_portal_role(self):
		supplier = _make_supplier("A1")
		user = _make_user("a1")

		_make_contact(user, suppliers=[supplier])

		user.reload()
		self.assertEqual(user.user_type, "Website User")
		self.assertIn(SUPPLIER_PORTAL_ROLE, [r.role for r in user.roles])

	def test_contact_link_without_supplier_does_not_grant_portal_role(self):
		user = _make_user("a2")
		original_roles = [r.role for r in user.roles]

		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": user.first_name,
				"user": user.name,
				"email_ids": [{"email_id": user.email, "is_primary": 1}],
			}
		)
		contact.insert(ignore_permissions=True)

		user.reload()
		self.assertNotIn(SUPPLIER_PORTAL_ROLE, [r.role for r in user.roles])
		self.assertEqual([r.role for r in user.roles], original_roles)

	def test_existing_staff_user_cannot_be_linked_as_supplier_portal_contact(self):
		supplier = _make_supplier("A3")
		staff_user = _make_user("a3", roles=["FreightMas User"])

		with self.assertRaises(frappe.ValidationError):
			_make_contact(staff_user, suppliers=[supplier])

	def test_manually_adding_desk_role_to_supplier_portal_user_is_rejected(self):
		supplier = _make_supplier("A4")
		user = _make_user("a4")
		_make_contact(user, suppliers=[supplier])

		user.reload()
		user.append("roles", {"role": "FreightMas User"})
		with self.assertRaises(frappe.ValidationError):
			user.save(ignore_permissions=True)

	def test_contact_can_link_multiple_suppliers(self):
		supplier_1 = _make_supplier("A5a")
		supplier_2 = _make_supplier("A5b")
		user = _make_user("a5")
		_make_contact(user, suppliers=[supplier_1, supplier_2])

		frappe.set_user(user.name)
		try:
			names = get_portal_supplier_names()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(set(names), {supplier_1.name, supplier_2.name})

	def test_contact_linked_to_both_customer_and_supplier_gets_both_roles(self):
		# Confirmed product decision: a broker who is legitimately both a
		# Customer and a Supplier gets both portal roles on one login,
		# rather than being rejected as a data-entry mistake.
		customer = _make_customer("A6")
		supplier = _make_supplier("A6")
		user = _make_user("a6")
		_make_contact(user, suppliers=[supplier], customers=[customer])

		user.reload()
		roles = [r.role for r in user.roles]
		self.assertIn(CUSTOMER_PORTAL_ROLE, roles)
		self.assertIn(SUPPLIER_PORTAL_ROLE, roles)


class TestCheckPortalAccessSupplier(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_rejects_guest(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			check_portal_access(role=SUPPLIER_PORTAL_ROLE)

	def test_rejects_unprovisioned_website_user(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "supplier.portal.test.unprovisioned@example.com",
				"first_name": "Unprovisioned",
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)

		frappe.set_user(user.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				check_portal_access(role=SUPPLIER_PORTAL_ROLE)
		finally:
			frappe.set_user("Administrator")

	def test_rejects_internal_staff_user(self):
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			check_portal_access(role=SUPPLIER_PORTAL_ROLE)

	def test_allows_provisioned_supplier_portal_user(self):
		supplier = _make_supplier("B1")
		user = _make_user("b1")
		_make_contact(user, suppliers=[supplier])

		frappe.set_user(user.name)
		try:
			check_portal_access(role=SUPPLIER_PORTAL_ROLE)  # must not raise
		finally:
			frappe.set_user("Administrator")

	def test_default_role_still_behaves_as_customer_portal_after_generalization(self):
		# Regression guard: check_portal_access() with no args must behave
		# identically for Customer-portal users after adding the role=
		# parameter - proof the generalization didn't change existing
		# Customer Portal behaviour.
		customer = _make_customer("B2")
		user = _make_user("b2")
		_make_contact(user, customers=[customer])

		frappe.set_user(user.name)
		try:
			check_portal_access()  # default role=CUSTOMER_PORTAL_ROLE, must not raise
			with self.assertRaises(frappe.PermissionError):
				check_portal_access(role=SUPPLIER_PORTAL_ROLE)
		finally:
			frappe.set_user("Administrator")


class TestAssertSupplierScope(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def _make_log(self, supplier):
		log = frappe.get_doc(
			{
				"doctype": "Client Portal Access Log",
				"user": frappe.session.user,
				"party_type": "Supplier",
				"party": supplier.name,
				"action": "test",
				"timestamp": frappe.utils.now(),
			}
		)
		log.insert(ignore_permissions=True)
		return log

	def test_allows_access_to_own_supplier_record(self):
		supplier = _make_supplier("C1")
		user = _make_user("c1")
		_make_contact(user, suppliers=[supplier])
		log = self._make_log(supplier)

		frappe.set_user(user.name)
		try:
			result = assert_supplier_scope("Client Portal Access Log", log.name, "party")
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result, supplier.name)

	def test_denies_access_to_other_suppliers_record(self):
		supplier_a = _make_supplier("C2a")
		supplier_b = _make_supplier("C2b")
		user_a = _make_user("c2a")
		_make_contact(user_a, suppliers=[supplier_a])
		log_for_b = self._make_log(supplier_b)

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				assert_supplier_scope("Client Portal Access Log", log_for_b.name, "party")
		finally:
			frappe.set_user("Administrator")

	def test_denies_unprovisioned_user_with_no_supplier_links(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "supplier.portal.test.c3@example.com",
				"first_name": "No Links",
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
		supplier = _make_supplier("C3")
		log = self._make_log(supplier)

		frappe.set_user(user.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				assert_supplier_scope("Client Portal Access Log", log.name, "party")
		finally:
			frappe.set_user("Administrator")


class TestSupplierScopedCharges(IntegrationTestCase):
	"""No Customer-portal precedent: a single Job's charge child table can
	carry rows from several different suppliers at once, mixed in with
	customer/sell_rate/margin fields on the very same row."""

	def setUp(self):
		frappe.set_user("Administrator")

	def test_returns_only_own_suppliers_rows_and_never_other_suppliers(self):
		customer = _make_customer("D1")
		supplier_a = _make_supplier("D1a")
		supplier_b = _make_supplier("D1b")
		job = _make_forwarding_job_with_charges(
			customer, "D1", [(supplier_a, 100), (supplier_a, 200), (supplier_b, 300)]
		)

		charges_a = get_supplier_scoped_charges("Forwarding Job", job.name, [supplier_a.name])
		rows_a = charges_a["forwarding_cost_charges"]
		self.assertEqual(len(rows_a), 2)
		self.assertTrue(all(r["supplier"] == supplier_a.name for r in rows_a))

		charges_b = get_supplier_scoped_charges("Forwarding Job", job.name, [supplier_b.name])
		rows_b = charges_b["forwarding_cost_charges"]
		self.assertEqual(len(rows_b), 1)
		self.assertEqual(rows_b[0]["supplier"], supplier_b.name)

	def test_never_leaks_customer_or_margin_fields(self):
		customer = _make_customer("D2")
		supplier = _make_supplier("D2")
		job = _make_forwarding_job_with_charges(customer, "D2", [(supplier, 100)])

		charges = get_supplier_scoped_charges("Forwarding Job", job.name, [supplier.name])
		rows = charges["forwarding_costing_charges"] + charges["forwarding_cost_charges"]
		self.assertTrue(rows, "expected at least one charge row for this supplier")

		leaky_keys = {"customer", "sell_rate", "revenue_amount", "margin_amount", "margin_percentage"}
		for row in rows:
			self.assertFalse(leaky_keys & set(row.keys()), f"leaked field(s) in row: {leaky_keys & set(row.keys())}")

	def test_supplier_with_no_rows_on_job_gets_empty_result_not_other_suppliers_rows(self):
		customer = _make_customer("D3")
		supplier_a = _make_supplier("D3a")
		supplier_c = _make_supplier("D3c")
		job = _make_forwarding_job_with_charges(customer, "D3", [(supplier_a, 100)])

		charges = get_supplier_scoped_charges("Forwarding Job", job.name, [supplier_c.name])
		self.assertEqual(charges["forwarding_cost_charges"], [])
