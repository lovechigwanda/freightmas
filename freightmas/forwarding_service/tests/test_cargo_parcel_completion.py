# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCargoParcelCompletion(FrappeTestCase):
	def _check(self, cargo_rows):
		job = frappe.new_doc("Forwarding Job")
		job.cargo_parcel_details = [frappe._dict(row) for row in cargo_rows]
		return job.check_cargo_parcel_requirements()

	def test_general_cargo_skips_return_by_date_requirement(self):
		errors = self._check([{
			"cargo_type": "General Cargo",
			"to_be_returned": 1,
			"return_by_date": None,
			"cargo_item_description": "Loose cartons",
		}])
		self.assertEqual(errors, [])

	def test_containerised_returnable_requires_return_by_date(self):
		errors = self._check([{
			"cargo_type": "Containerised",
			"container_number": "MEDU4860148",
			"to_be_returned": 1,
			"return_by_date": None,
		}])
		self.assertTrue(any("Return By Date" in error for error in errors))
