# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd

import frappe
from frappe.tests.utils import FrappeTestCase

from freightmas.forwarding_service.utils.cargo_milestone_sync import (
	sync_loaded_milestone_from_gate_out,
	sync_return_milestone_from_empty_return,
)


class TestCargoMilestoneSync(FrappeTestCase):
	def _make_cargo(self, **kwargs):
		row = frappe._dict({
			"is_truck_required": 1,
			"is_booked": 0,
			"is_loaded": 0,
			"loaded_on_date": None,
			"loaded_milestone_source": "",
			"gate_out_date": None,
			"to_be_returned": 1,
			"is_offloaded": 0,
			"is_returned": 0,
			"returned_on_date": None,
			"return_milestone_source": "",
			"empty_return_date": None,
		})
		row.update(kwargs)
		return row

	def test_gate_out_requires_booked(self):
		row = self._make_cargo(is_booked=0, gate_out_date="2026-07-20")
		self.assertFalse(sync_loaded_milestone_from_gate_out(row))
		self.assertFalse(row.is_loaded)

	def test_gate_out_sets_loaded_and_date(self):
		row = self._make_cargo(is_booked=1, gate_out_date="2026-07-20")
		self.assertTrue(sync_loaded_milestone_from_gate_out(row))
		self.assertEqual(row.is_loaded, 1)
		self.assertEqual(str(row.loaded_on_date), "2026-07-20")
		self.assertEqual(row.loaded_milestone_source, "API")

	def test_empty_return_requires_offloaded(self):
		row = self._make_cargo(is_offloaded=0, empty_return_date="2026-08-01")
		self.assertFalse(sync_return_milestone_from_empty_return(row))
		self.assertFalse(row.is_returned)

	def test_empty_return_sets_returned_and_date(self):
		row = self._make_cargo(is_offloaded=1, empty_return_date="2026-08-01")
		self.assertTrue(sync_return_milestone_from_empty_return(row))
		self.assertEqual(row.is_returned, 1)
		self.assertEqual(str(row.returned_on_date), "2026-08-01")
		self.assertEqual(row.return_milestone_source, "API")

	def test_manual_loaded_not_overwritten(self):
		row = self._make_cargo(
			is_booked=1,
			is_loaded=1,
			loaded_on_date="2026-07-15",
			loaded_milestone_source="Manual",
			gate_out_date="2026-07-20",
		)
		self.assertFalse(sync_loaded_milestone_from_gate_out(row))
		self.assertEqual(str(row.loaded_on_date), "2026-07-15")
