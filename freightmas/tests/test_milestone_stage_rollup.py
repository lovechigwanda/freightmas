# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Unit tests for the milestone stage rollup - the pure logic behind the
summarized (stage-level) client report view. No DB fixtures needed: these
exercise milestone_stage_rollup() / has_milestone_stages() directly on plain
milestone dicts, the same shape they receive from Job Milestone Progress rows.
"""

import unittest

from freightmas.freightmas.page.shipment_dashboard.shipment_dashboard import (
	has_milestone_stages,
	milestone_stage_rollup,
)


def _m(label, stage, seq, done):
	return {"label": label, "stage": stage, "stage_sequence": seq, "is_completed": done}


class TestMilestoneStageRollup(unittest.TestCase):
	def test_orders_by_stage_sequence_and_counts(self):
		milestones = [
			_m("Customs Entry", "Customs", 3, False),
			_m("Pre-Alert", "Documentation", 1, True),
			_m("Bill of Lading", "Documentation", 1, True),
			_m("SL BL Released", "Shipping Line", 2, False),
		]
		stages = milestone_stage_rollup(milestones)
		self.assertEqual([s["name"] for s in stages], ["Documentation", "Shipping Line", "Customs"])
		docs = stages[0]
		self.assertEqual((docs["done"], docs["total"], docs["pct"]), (2, 2, 100))

	def test_current_stage_is_first_incomplete(self):
		milestones = [
			_m("Pre-Alert", "Documentation", 1, True),
			_m("SL BL Released", "Shipping Line", 2, False),
			_m("Customs Entry", "Customs", 3, False),
		]
		stages = milestone_stage_rollup(milestones)
		current = [s["name"] for s in stages if s["is_current"]]
		self.assertEqual(current, ["Shipping Line"])

	def test_no_current_when_all_complete(self):
		milestones = [
			_m("Pre-Alert", "Documentation", 1, True),
			_m("Customs Entry", "Customs", 3, True),
		]
		stages = milestone_stage_rollup(milestones)
		self.assertFalse(any(s["is_current"] for s in stages))

	def test_unstaged_milestones_bucket_last(self):
		milestones = [
			_m("Loose Step", None, 0, False),
			_m("Pre-Alert", "Documentation", 1, True),
		]
		stages = milestone_stage_rollup(milestones)
		self.assertEqual(stages[-1]["name"], "Other")
		self.assertEqual([s["name"] for s in stages], ["Documentation", "Other"])

	def test_has_milestone_stages(self):
		self.assertTrue(has_milestone_stages([_m("a", "Documentation", 1, False)]))
		self.assertFalse(has_milestone_stages([_m("a", None, 0, False)]))
		self.assertFalse(has_milestone_stages([]))

	def test_missing_lists_incomplete_labels_per_stage(self):
		milestones = [
			_m("Bill of Lading", "Documentation", 1, False),
			_m("Endorsement Letter", "Documentation", 1, False),
			_m("Pre-Alert", "Documentation", 1, True),
			_m("SL BL Released", "Shipping Line", 2, False),
		]
		stages = milestone_stage_rollup(milestones)
		docs, shipping_line = stages[0], stages[1]
		self.assertEqual(docs["missing"], ["Bill of Lading", "Endorsement Letter"])
		self.assertEqual(shipping_line["missing"], ["SL BL Released"])

	def test_missing_empty_when_stage_fully_complete(self):
		milestones = [_m("Pre-Alert", "Documentation", 1, True)]
		stages = milestone_stage_rollup(milestones)
		self.assertEqual(stages[0]["missing"], [])


if __name__ == "__main__":
	unittest.main()
