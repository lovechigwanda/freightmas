# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and Contributors
# See license.txt

import unittest

from freightmas.trucking_service.doctype.trip.assignment_snapshot import (
	apply_truck_assignment_snapshot,
	resolve_legacy_driver_value,
)


class _Trip:
	def __init__(self, **kwargs):
		self.truck = None
		self.horse = None
		self.trailer = None
		self.driver = None
		self.s_warehouse = None
		self.driver_name = None
		self.__dict__.update(kwargs)


class TestTripAssignmentSnapshot(unittest.TestCase):
	def test_new_truck_copies_driver_horse_trailer_and_warehouse(self):
		trip = _Trip()
		truck = {
			"horse": "AEZ-1234",
			"assigned_trailer": "TRL-99",
			"assigned_driver": "HR-DRV-0001",
			"warehouse": "Fuel WH",
		}

		apply_truck_assignment_snapshot(trip, truck, truck_changed=True)

		self.assertEqual(trip.horse, "AEZ-1234")
		self.assertEqual(trip.trailer, "TRL-99")
		self.assertEqual(trip.driver, "HR-DRV-0001")
		self.assertEqual(trip.s_warehouse, "Fuel WH")

	def test_truck_master_change_does_not_overwrite_existing_assignment(self):
		trip = _Trip(
			horse="AEZ-1234",
			trailer="TRL-99",
			driver="HR-DRV-0001",
			s_warehouse="Fuel WH",
		)
		truck = {
			"horse": "AEZ-1234",
			"assigned_trailer": "TRL-NEW",
			"assigned_driver": "HR-DRV-0002",
			"warehouse": "Other WH",
		}

		apply_truck_assignment_snapshot(trip, truck, truck_changed=False)

		self.assertEqual(trip.driver, "HR-DRV-0001")
		self.assertEqual(trip.trailer, "TRL-99")
		self.assertEqual(trip.s_warehouse, "Fuel WH")

	def test_explicit_driver_on_truck_change_is_kept(self):
		trip = _Trip(driver="HR-DRV-RELIEF")
		truck = {
			"horse": "AEZ-1234",
			"assigned_trailer": "TRL-99",
			"assigned_driver": "HR-DRV-0001",
			"warehouse": "Fuel WH",
		}

		apply_truck_assignment_snapshot(
			trip,
			truck,
			truck_changed=True,
			driver_explicitly_set=True,
		)

		self.assertEqual(trip.driver, "HR-DRV-RELIEF")
		self.assertEqual(trip.horse, "AEZ-1234")
		self.assertEqual(trip.trailer, "TRL-99")

	def test_explicit_trailer_on_truck_change_is_kept(self):
		trip = _Trip(trailer="TRL-SWAP")
		truck = {
			"horse": "AEZ-1234",
			"assigned_trailer": "TRL-99",
			"assigned_driver": "HR-DRV-0001",
			"warehouse": "Fuel WH",
		}

		apply_truck_assignment_snapshot(
			trip,
			truck,
			truck_changed=True,
			trailer_explicitly_set=True,
		)

		self.assertEqual(trip.trailer, "TRL-SWAP")
		self.assertEqual(trip.driver, "HR-DRV-0001")

	def test_empty_fields_are_backfilled_without_overwriting(self):
		trip = _Trip(driver="HR-DRV-0001")
		truck = {
			"horse": "AEZ-1234",
			"assigned_trailer": "TRL-99",
			"assigned_driver": "HR-DRV-0002",
			"warehouse": "Fuel WH",
		}

		apply_truck_assignment_snapshot(trip, truck, truck_changed=False)

		self.assertEqual(trip.driver, "HR-DRV-0001")
		self.assertEqual(trip.horse, "AEZ-1234")
		self.assertEqual(trip.trailer, "TRL-99")
		self.assertEqual(trip.s_warehouse, "Fuel WH")


class TestResolveLegacyDriverValue(unittest.TestCase):
	def test_keeps_existing_driver_id(self):
		driver_id, fallback = resolve_legacy_driver_value(
			"HR-DRV-0001",
			driver_ids={"HR-DRV-0001"},
		)
		self.assertEqual(driver_id, "HR-DRV-0001")
		self.assertIsNone(fallback)

	def test_maps_full_name_to_single_driver(self):
		driver_id, fallback = resolve_legacy_driver_value(
			"Jane Driver",
			driver_ids={"HR-DRV-0001"},
			full_name_to_ids={"Jane Driver": ["HR-DRV-0001"]},
		)
		self.assertEqual(driver_id, "HR-DRV-0001")
		self.assertEqual(fallback, "Jane Driver")

	def test_ambiguous_name_prefers_truck_driver(self):
		driver_id, fallback = resolve_legacy_driver_value(
			"John Smith",
			truck_assigned_driver="HR-DRV-0002",
			driver_ids={"HR-DRV-0001", "HR-DRV-0002"},
			full_name_to_ids={"John Smith": ["HR-DRV-0001", "HR-DRV-0002"]},
		)
		self.assertEqual(driver_id, "HR-DRV-0002")
		self.assertEqual(fallback, "John Smith")

	def test_unresolved_name_is_kept_as_display_and_not_guessed(self):
		driver_id, fallback = resolve_legacy_driver_value(
			"Unknown Person",
			truck_assigned_driver="HR-DRV-0001",
			driver_ids={"HR-DRV-0001"},
			full_name_to_ids={"Jane Driver": ["HR-DRV-0001"]},
		)
		self.assertIsNone(driver_id)
		self.assertEqual(fallback, "Unknown Person")

	def test_empty_driver_falls_back_to_truck_assignment(self):
		driver_id, fallback = resolve_legacy_driver_value(
			"",
			truck_assigned_driver="HR-DRV-0001",
			driver_ids={"HR-DRV-0001"},
		)
		self.assertEqual(driver_id, "HR-DRV-0001")
		self.assertIsNone(fallback)
