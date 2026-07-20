# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Phase 0 tests for the Client Portal security foundation.

Covers freightmas.portal.security and freightmas.portal.provisioning: the
Contact -> User -> Customer provisioning constraints, the check_portal_access
gate, get_portal_customer_names resolution, and assert_customer_scope's
generic scoping logic (exercised here against Client Portal Access Log,
the one doctype this phase actually ships, since no portal-facing job/
invoice API endpoints exist yet).

Full cross-tenant coverage against Forwarding Job / Sales Invoice /
Payment Entry belongs with the Phase 1/2 API endpoints that will read
those doctypes - see the plan at
~/.claude/plans/after-the-command-centre-zany-garden.md.

Uses frappe.tests.IntegrationTestCase (the current, non-deprecated
replacement for frappe.tests.utils.FrappeTestCase) so every test runs
inside a rolled-back savepoint.
"""

import frappe
from frappe.tests import IntegrationTestCase

from freightmas.portal.attachments import PROTECTED_DOCTYPES, enforce_private_on_insert
from freightmas.portal.security import (
	PORTAL_ROLE,
	assert_customer_scope,
	check_portal_access,
	get_portal_customer_names,
)


def _make_customer(suffix):
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"Portal Test Customer {suffix}",
			"customer_type": "Company",
			"customer_group": "Commercial",
			"territory": "Zimbabwe",
		}
	)
	customer.insert(ignore_permissions=True)
	return customer


def _make_user(suffix, roles=None):
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": f"portal.test.{suffix}@example.com",
			"first_name": f"Portal Test {suffix}",
			"send_welcome_email": 0,
		}
	)
	for role in roles or []:
		user.append("roles", {"role": role})
	user.insert(ignore_permissions=True)
	return user


def _make_contact(user, customers):
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": user.first_name,
			"user": user.name,
			"email_ids": [{"email_id": user.email, "is_primary": 1}],
		}
	)
	for customer in customers:
		contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	contact.insert(ignore_permissions=True)
	return contact


class TestClientPortalProvisioning(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_contact_with_customer_link_forces_website_user_and_portal_role(self):
		customer = _make_customer("A1")
		user = _make_user("a1")

		_make_contact(user, [customer])

		user.reload()
		self.assertEqual(user.user_type, "Website User")
		self.assertIn(PORTAL_ROLE, [r.role for r in user.roles])

	def test_contact_link_without_customer_does_not_grant_portal_role(self):
		# Core Frappe itself flips a Contact-linked User's user_type to
		# Website User regardless of Customer links - that's expected,
		# unrelated to this feature. What matters here is that our own
		# provisioning hook is a no-op without a Customer link: no portal
		# role, no forced role changes, since there is nothing to scope
		# access to.
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
		self.assertNotIn(PORTAL_ROLE, [r.role for r in user.roles])
		self.assertEqual([r.role for r in user.roles], original_roles)

	def test_existing_staff_user_cannot_be_linked_as_portal_contact(self):
		customer = _make_customer("A3")
		staff_user = _make_user("a3", roles=["FreightMas User"])

		with self.assertRaises(frappe.ValidationError):
			_make_contact(staff_user, [customer])

	def test_manually_adding_desk_role_to_portal_user_is_rejected(self):
		customer = _make_customer("A4")
		user = _make_user("a4")
		_make_contact(user, [customer])

		user.reload()
		user.append("roles", {"role": "FreightMas User"})
		with self.assertRaises(frappe.ValidationError):
			user.save(ignore_permissions=True)

	def test_contact_can_link_multiple_customers(self):
		customer_1 = _make_customer("A5a")
		customer_2 = _make_customer("A5b")
		user = _make_user("a5")
		_make_contact(user, [customer_1, customer_2])

		frappe.set_user(user.name)
		try:
			names = get_portal_customer_names()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(set(names), {customer_1.name, customer_2.name})

	def test_customer_names_resolve_across_multiple_contacts_for_same_user(self):
		# A user can end up with more than one Contact record (observed in
		# production: separate Client/Supplier Portal provisioning attempts
		# for the same email each create their own Contact). get_portal_
		# party_names() must aggregate Dynamic Links across all of a user's
		# Contacts, not silently resolve to whichever one an unordered query
		# happens to return first - see freightmas-client-portal memory.
		customer = _make_customer("A6")
		user = _make_user("a6")

		# First Contact: no Customer link (e.g. a bare/legacy record).
		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": user.first_name,
				"user": user.name,
				"email_ids": [{"email_id": f"a6-first@example.com", "is_primary": 1}],
			}
		).insert(ignore_permissions=True)

		# Second Contact for the same user: this is the one with the real link.
		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": user.first_name,
				"user": user.name,
				"email_ids": [{"email_id": f"a6-second@example.com", "is_primary": 1}],
				"links": [{"link_doctype": "Customer", "link_name": customer.name}],
			}
		).insert(ignore_permissions=True)

		frappe.set_user(user.name)
		try:
			names = get_portal_customer_names()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(names, [customer.name])


class TestCheckPortalAccess(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_rejects_guest(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			check_portal_access()

	def test_rejects_unprovisioned_website_user(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "portal.test.unprovisioned@example.com",
				"first_name": "Unprovisioned",
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)

		frappe.set_user(user.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				check_portal_access()
		finally:
			frappe.set_user("Administrator")

	def test_rejects_internal_staff_user(self):
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			# Administrator is a System User with desk_access roles - must
			# never pass the portal gate even though it is a valid session.
			check_portal_access()

	def test_allows_provisioned_portal_user(self):
		customer = _make_customer("B1")
		user = _make_user("b1")
		_make_contact(user, [customer])

		frappe.set_user(user.name)
		try:
			check_portal_access()  # must not raise
		finally:
			frappe.set_user("Administrator")


class TestAssertCustomerScope(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def _make_log(self, customer):
		log = frappe.get_doc(
			{
				"doctype": "Client Portal Access Log",
				"user": frappe.session.user,
				"customer": customer.name,
				"action": "test",
				"timestamp": frappe.utils.now(),
			}
		)
		log.insert(ignore_permissions=True)
		return log

	def test_allows_access_to_own_customer_record(self):
		customer = _make_customer("C1")
		user = _make_user("c1")
		_make_contact(user, [customer])
		log = self._make_log(customer)

		frappe.set_user(user.name)
		try:
			result = assert_customer_scope("Client Portal Access Log", log.name, "customer")
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result, customer.name)

	def test_denies_access_to_other_customers_record(self):
		customer_a = _make_customer("C2a")
		customer_b = _make_customer("C2b")
		user_a = _make_user("c2a")
		_make_contact(user_a, [customer_a])
		log_for_b = self._make_log(customer_b)

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				assert_customer_scope("Client Portal Access Log", log_for_b.name, "customer")
		finally:
			frappe.set_user("Administrator")

	def test_denies_unprovisioned_user_with_no_customer_links(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "portal.test.c3@example.com",
				"first_name": "No Links",
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
		customer = _make_customer("C3")
		log = self._make_log(customer)

		frappe.set_user(user.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				assert_customer_scope("Client Portal Access Log", log.name, "customer")
		finally:
			frappe.set_user("Administrator")


class TestEnforcePrivateOnInsert(IntegrationTestCase):
	def test_forces_private_on_protected_doctype(self):
		self.assertIn("Forwarding Job", PROTECTED_DOCTYPES)
		file_doc = frappe.new_doc("File")
		file_doc.attached_to_doctype = "Forwarding Job"
		file_doc.is_private = 0

		enforce_private_on_insert(file_doc)

		self.assertEqual(file_doc.is_private, 1)

	def test_leaves_unrelated_doctype_untouched(self):
		file_doc = frappe.new_doc("File")
		file_doc.attached_to_doctype = "Note"
		file_doc.is_private = 0

		enforce_private_on_insert(file_doc)

		self.assertEqual(file_doc.is_private, 0)
