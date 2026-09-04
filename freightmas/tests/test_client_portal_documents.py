# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Client Portal document access tests for Forwarding Job documentation."""

from io import BytesIO
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import cint, nowdate
from werkzeug.datastructures import FileStorage

from freightmas.portal.api import documents as portal_documents
from freightmas.tests.test_client_portal_shipments import _make_pair

TEST_PNG = (
	b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
	b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
	b"\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


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


def _add_checklist_row(
	job,
	suffix,
	*,
	client_view=0,
	client_upload=0,
	uploaded_by_client=0,
	attach=None,
	is_verified=0,
):
	job = frappe.get_doc("Forwarding Job", job.name)
	job.append(
		"documents_checklist",
		{
			"document": f"Portal Test Doc {suffix}",
			"attach": attach,
			"client_view": client_view,
			"client_upload": client_upload,
			"uploaded_by_client": uploaded_by_client,
			"is_submitted": 1 if attach else 0,
			"date_submitted": nowdate() if attach else None,
			"is_verified": is_verified,
		},
	)
	job.save(ignore_permissions=True)
	return job.documents_checklist[-1]


def _add_client_visible_document(job, suffix, *, client_view=1, attach=None):
	return _add_checklist_row(job, suffix, client_view=client_view, attach=attach)


def _mock_upload(file_name, content, **form_fields):
	frappe.local.request = frappe._dict()
	frappe.local.request.files = frappe._dict(
		{
			"file": FileStorage(
				stream=BytesIO(content),
				filename=file_name,
				content_type="application/octet-stream",
			)
		}
	)
	frappe.form_dict = frappe._dict(form_fields)


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

	def test_get_job_documents_includes_requested_incoming_row(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D5")
		self._ensure_clearing_document("Portal Test Doc D5a")
		requested = _add_checklist_row(job_a, "D5a", client_upload=1)

		frappe.set_user(user_a.name)
		try:
			result = portal_documents.get_job_documents(job_a.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(len(result["incoming"]), 1)
		self.assertEqual(result["incoming"][0]["name"], requested.name)
		self.assertTrue(result["incoming"][0]["can_upload"])
		self.assertFalse(result["incoming"][0]["can_download"])

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
			self.assertEqual(
				frappe.local.response.filecontent,
				b"portal document test content"
				if isinstance(frappe.local.response.filecontent, bytes)
				else "portal document test content",
			)
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

	def test_upload_to_requested_row(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D6")
		self._ensure_clearing_document("Portal Test Doc D6a")
		row = _add_checklist_row(job_a, "D6a", client_upload=1)

		frappe.set_user(user_a.name)
		try:
			_mock_upload(
				"bill-of-lading.png",
				TEST_PNG,
				job_name=job_a.name,
				checklist_row=row.name,
			)
			with patch("freightmas.portal.api.documents.send_client_document_upload_email"):
				result = portal_documents.upload_job_document()

			job = frappe.get_doc("Forwarding Job", job_a.name)
			updated = next(r for r in job.documents_checklist if r.name == row.name)
			self.assertTrue(updated.attach)
			self.assertTrue(updated.is_submitted)
			self.assertEqual(result["file_name"], "bill-of-lading.png")
			self.assertTrue(result["can_download"])
			file_doc = frappe.db.get_value("File", {"file_url": updated.attach}, ["is_private"], as_dict=True)
			self.assertEqual(cint(file_doc.is_private), 1)
		finally:
			frappe.set_user("Administrator")

	def test_ad_hoc_upload_creates_incoming_row(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D7")
		doc_name = "Portal Test Doc D7a"
		self._ensure_clearing_document(doc_name)

		frappe.set_user(user_a.name)
		try:
			_mock_upload(
				"packing-list.png",
				TEST_PNG,
				job_name=job_a.name,
				document=doc_name,
			)
			with patch("freightmas.portal.api.documents.send_client_document_upload_email"):
				result = portal_documents.upload_job_document()

			job = frappe.get_doc("Forwarding Job", job_a.name)
			created = next(r for r in job.documents_checklist if r.document == doc_name)
			self.assertTrue(created.uploaded_by_client)
			self.assertFalse(created.client_view)
			self.assertEqual(result["document_label"], doc_name)
			self.assertTrue(result["is_ad_hoc"])
		finally:
			frappe.set_user("Administrator")

	def test_upload_denies_other_customers_job(self):
		_customer_a, _customer_b, user_a, _job_a, job_b = _make_pair("D8")
		self._ensure_clearing_document("Portal Test Doc D8a")
		row = _add_checklist_row(job_b, "D8a", client_upload=1)

		frappe.set_user(user_a.name)
		try:
			_mock_upload("invoice.png", TEST_PNG, job_name=job_b.name, checklist_row=row.name)
			with self.assertRaises(frappe.PermissionError):
				portal_documents.upload_job_document()
		finally:
			frappe.set_user("Administrator")

	def test_upload_denies_non_eligible_row(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D9")
		self._ensure_clearing_document("Portal Test Doc D9a")
		row = _add_checklist_row(job_a, "D9a")

		frappe.set_user(user_a.name)
		try:
			_mock_upload("invoice.png", TEST_PNG, job_name=job_a.name, checklist_row=row.name)
			with self.assertRaises(frappe.PermissionError):
				portal_documents.upload_job_document()
		finally:
			frappe.set_user("Administrator")

	def test_upload_denies_verified_row(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D10")
		self._ensure_clearing_document("Portal Test Doc D10a")
		row = _add_checklist_row(job_a, "D10a", client_upload=1, is_verified=1)

		frappe.set_user(user_a.name)
		try:
			_mock_upload("invoice.png", TEST_PNG, job_name=job_a.name, checklist_row=row.name)
			with self.assertRaises(frappe.ValidationError):
				portal_documents.upload_job_document()
		finally:
			frappe.set_user("Administrator")

	def test_upload_denies_closed_job(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D11")
		self._ensure_clearing_document("Portal Test Doc D11a")
		row = _add_checklist_row(job_a, "D11a", client_upload=1)
		frappe.db.set_value("Forwarding Job", job_a.name, "status", "Completed")

		frappe.set_user(user_a.name)
		try:
			_mock_upload("invoice.png", TEST_PNG, job_name=job_a.name, checklist_row=row.name)
			with self.assertRaises(frappe.ValidationError):
				portal_documents.upload_job_document()
		finally:
			frappe.set_user("Administrator")

	def test_download_incoming_upload(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D12")
		self._ensure_clearing_document("Portal Test Doc D12a")
		row = _add_checklist_row(job_a, "D12a", client_upload=1)

		frappe.set_user(user_a.name)
		try:
			_mock_upload(
				"commercial-invoice.png",
				TEST_PNG,
				job_name=job_a.name,
				checklist_row=row.name,
			)
			with patch("freightmas.portal.api.documents.send_client_document_upload_email"):
				portal_documents.upload_job_document()

			job = frappe.get_doc("Forwarding Job", job_a.name)
			updated = next(r for r in job.documents_checklist if r.name == row.name)
			portal_documents.download_job_document(job_a.name, updated.name)
			self.assertEqual(frappe.local.response.type, "download")
			self.assertEqual(frappe.local.response.filename, "commercial-invoice.png")
		finally:
			frappe.set_user("Administrator")

	def test_upload_rejects_invalid_extension(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D13")
		self._ensure_clearing_document("Portal Test Doc D13a")
		row = _add_checklist_row(job_a, "D13a", client_upload=1)

		frappe.set_user(user_a.name)
		try:
			_mock_upload("malware.exe", b"bad", job_name=job_a.name, checklist_row=row.name)
			with self.assertRaises(frappe.ValidationError):
				portal_documents.upload_job_document()
		finally:
			frappe.set_user("Administrator")

	def test_upload_rejects_oversized_file(self):
		_customer_a, _customer_b, user_a, job_a, _job_b = _make_pair("D14")
		self._ensure_clearing_document("Portal Test Doc D14a")
		row = _add_checklist_row(job_a, "D14a", client_upload=1)

		frappe.set_user(user_a.name)
		try:
			_mock_upload(
				"huge.png",
				b"x" * (portal_documents.MAX_UPLOAD_SIZE_BYTES + 1),
				job_name=job_a.name,
				checklist_row=row.name,
			)
			with self.assertRaises(frappe.ValidationError):
				portal_documents.upload_job_document()
		finally:
			frappe.set_user("Administrator")
