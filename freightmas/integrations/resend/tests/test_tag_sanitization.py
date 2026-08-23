# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import unittest

from freightmas.integrations.resend.validation import sanitize_resend_tag


class TestResendTagSanitization(unittest.TestCase):
	def test_doctype_with_spaces(self):
		self.assertEqual(sanitize_resend_tag("Forwarding Job"), "Forwarding_Job")

	def test_owner_email(self):
		self.assertEqual(sanitize_resend_tag("user@company.co.zw"), "user_company_co_zw")

	def test_empty_or_invalid_values(self):
		self.assertIsNone(sanitize_resend_tag(""))
		self.assertIsNone(sanitize_resend_tag("   "))
		self.assertIsNone(sanitize_resend_tag("!!!"))

	def test_truncates_to_256_chars(self):
		value = "a" * 300
		self.assertEqual(len(sanitize_resend_tag(value)), 256)


if __name__ == "__main__":
	unittest.main()
