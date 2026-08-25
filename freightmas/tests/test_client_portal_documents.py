# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Client Portal document access tests for Forwarding Job documentation."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from freightmas.portal.api import documents as portal_documents
from freightmas.tests.test_client_portal_shipments import _make_pair


def _attach_test_file(job, file_name="portal-test-doc.txt"):
	content = b"portal document test content"
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": "Forwarding Job",
			"attached_to_name": job.name,
			"attached_to_field": "documents_checklist",
			"is_private": 1,
			"content": content,
		}
	)
	file_doc.insert(ignore_permissions=True)
	return file_doc


def _add_client_visible_document(job, suffix, *, client_view=1, attach=None):
	job = frappe.get_doc("Forwarding Job", job.name)
	job.append(
		"documents_checklist",
		{
			"document": f"Portal Test Doc {suffix}",
			"attach": attach,
			"client_view": client_view,
			"is_submitted": 1,
			"date_submitted": nowdate(),
		},
	)
	job.save(ignore_permissions=True)
	return job.documents_checklist[-1]


class TestPortalDocuments(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def _ensure_clearing_document(self, name):
		if not frappe.db.exists("Clearing Document", name):
			frappe.get_doc({"doctype": "Clearing Document", "document_name": name}).insert(
				ignore_permissions=True
			)

	def test_get_job_documents_returns_client_view_outgoing_only(self):
		customer_a, _customer_b, user_a, job_a, job_b = _make_pair("D1")
		self._ensure_clearing_document("Portal Test Doc D1a")
		self._ensure_clearing_document("Portal Test Doc D1b")
		self._ensure_clearing_document("Portal Test Doc D1c")

		file_a = _attach_test_file(job_a, "client-visible.txt")
		file_b = _attach_test_file(job_b, "other-customer.txt")

		visible_row = _add_client_visible_document(
			job_a,
			"D1a",
			client_view=1,
			attach=file_a.file_url,
		)
		_add_client_visible_document(job_a, "D1b", client_view=0, attach=file_a.file_url)
		_add_client_visible_document(job_b, "D1c", client_view=1, attach=file_b.file_url)

		frappe.set_user(user_a.name)
		try:
			result = portal_documents.get_job_documents(job_a.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(len(result["outgoing"]), 1)
		self.assertEqual(result["outgoing"][0]["name"], visible_row.name)
		self.assertEqual(result["outgoing"][0]["document_label"], "Portal Test Doc D1a")
		self.assertEqual(result["incoming"], [])

	def test_get_job_documents_denies_other_customers_job(self):
		_customer_a, _customer_b, user_a, _job_a, job_b = _make_pair("D2")

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_documents.get_job_documents(job_b.name)
		finally:
			frappe.set_user("Administrator")

	def test_download_job_document_streams_scoped_file(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D3")
		self._ensure_clearing_document("Portal Test Doc D3a")
		file_a = _attach_test_file(job_a, "download-me.txt")
		row = _add_client_visible_document(job_a, "D3a", client_view=1, attach=file_a.file_url)

		frappe.set_user(user_a.name)
		try:
			portal_documents.download_job_document(job_a.name, row.name)
			self.assertEqual(frappe.local.response.type, "download")
			self.assertEqual(frappe.local.response.filename, "download-me.txt")
			self.assertEqual(frappe.local.response.filecontent, b"portal document test content" if isinstance(frappe.local.response.filecontent, bytes) else "portal document test content")
		finally:
			frappe.set_user("Administrator")

	def test_download_job_document_denies_non_client_view_row(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D4")
		self._ensure_clearing_document("Portal Test Doc D4a")
		file_a = _attach_test_file(job_a, "hidden.txt")
		row = _add_client_visible_document(job_a, "D4a", client_view=0, attach=file_a.file_url)

		frappe.set_user(user_a.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				portal_documents.download_job_document(job_a.name, row.name)
		finally:
			frappe.set_user("Administrator")
