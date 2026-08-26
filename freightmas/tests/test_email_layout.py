# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Tests for FreightMas email layout helpers."""

import unittest

from freightmas.utils.email_layout import (
	is_wrapped_email,
	prepare_email_body,
	render_detail_card,
	render_freightmas_email,
)


class TestEmailLayout(unittest.TestCase):
	def test_prepare_email_body_plain_text(self):
		html = prepare_email_body("Hello there.\n\nSecond paragraph.")
		self.assertIn("<p", html)
		self.assertIn("Hello there.", html)
		self.assertIn("Second paragraph.", html)

	def test_prepare_email_body_preserves_html(self):
		source = "<p>Already HTML</p>"
		self.assertEqual(prepare_email_body(source), source)

	def test_render_detail_card_skips_empty_values(self):
		html = render_detail_card("Details", [("Job", "J-1"), ("Empty", "")])
		self.assertIn("J-1", html)
		self.assertNotIn("Empty", html)

	def test_render_freightmas_email_wraps_body(self):
		html = render_freightmas_email(
			"<p>Body copy</p>",
			company=None,
			email_type="SHIPMENT NOTIFICATION",
		)
		self.assertTrue(is_wrapped_email(html))
		self.assertIn("SHIPMENT NOTIFICATION", html)
		self.assertIn("Body copy", html)
		self.assertIn("confidential", html.lower())

	def test_render_freightmas_email_skips_double_wrap(self):
		inner = render_freightmas_email("<p>Once</p>", email_type="TRACKING REPORT")
		again = render_freightmas_email(inner, email_type="TRACKING REPORT")
		self.assertEqual(inner, again)
