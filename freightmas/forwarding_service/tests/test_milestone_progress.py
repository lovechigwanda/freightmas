# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import unittest

from freightmas.forwarding_service.utils.milestone_progress import (
	overall_milestone_percent,
	road_transport_progress_counts,
	sea_air_progress_counts,
)


class TestMilestoneProgress(unittest.TestCase):
	def test_road_transport_counts_truck_parcel(self):
		parcels = [{
			"is_truck_required": 1,
			"cargo_type": "Loose",
			"is_booked": 1,
			"is_loaded": 1,
			"is_offloaded": 0,
			"is_completed": 0,
		}]
		total, done = road_transport_progress_counts(parcels)
		self.assertEqual(total, 4)
		self.assertEqual(done, 2)

	def test_road_transport_returnable_container_adds_return_check(self):
		parcels = [{
			"is_truck_required": 1,
			"cargo_type": "Containerised",
			"to_be_returned": 1,
			"is_booked": 1,
			"is_loaded": 1,
			"is_offloaded": 1,
			"is_completed": 1,
			"is_returned": 0,
			"empty_return_date": None,
		}]
		total, done = road_transport_progress_counts(parcels)
		self.assertEqual(total, 5)
		self.assertEqual(done, 4)

	def test_sea_air_counts_shipment_and_container_dates(self):
		job = {"atd": "2026-07-01", "ata": None}
		parcels = [{
			"cargo_type": "Containerised",
			"discharge_date": "2026-07-10",
			"gate_out_date": None,
			"to_be_returned": 1,
			"empty_return_date": None,
		}]
		total, done = sea_air_progress_counts(job, parcels)
		self.assertEqual(total, 5)
		self.assertEqual(done, 2)

	def test_overall_percent(self):
		self.assertEqual(overall_milestone_percent(8, 2), 25)
		self.assertEqual(overall_milestone_percent(0, 0), 0)


if __name__ == "__main__":
	unittest.main()
