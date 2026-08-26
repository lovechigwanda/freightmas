# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Regression tests for Traqo multi-container BL event parsing."""

import unittest

from freightmas.integrations.tracking.base import location_matches, parse_container_events
from freightmas.integrations.tracking.traqo import _events_for_container, _parse_containers


def _beira_bl_fixture():
	"""Synthetic Traqo BL payload modelled on FWJB-00015-26 / MSC Beira import."""
	events = [
		{"idx": 1, "event_code": "GTOT", "timestamp": "2026-05-13 00:00:00", "location": "Xiamen", "is_actual": 1, "description": "Empty to Shipper", "container_number": "MEDU5945450"},
		{"idx": 2, "event_code": "DISC", "timestamp": "2026-05-29 00:00:00", "location": "Singapore", "is_actual": 1, "description": "Full Transshipment Discharged", "container_number": "MEDU5945450"},
		{"idx": 3, "event_code": "DISC", "timestamp": "2026-08-10 00:00:00", "location": "Beira", "is_actual": 1, "description": "Import Discharged from Vessel", "container_number": "MEDU5945450"},
		{"idx": 4, "event_code": "GTOT", "timestamp": "2026-08-19 00:00:00", "location": "Beira", "is_actual": 1, "description": "Import to consignee", "container_number": "MEDU5945450"},
		{"idx": 5, "event_code": "GTOT", "timestamp": "2026-05-13 00:00:00", "location": "Xiamen", "is_actual": 1, "description": "Empty to Shipper", "container_number": "TGBU3890006"},
		{"idx": 6, "event_code": "DISC", "timestamp": "2026-05-29 00:00:00", "location": "Singapore", "is_actual": 1, "description": "Full Transshipment Discharged", "container_number": "TGBU3890006"},
		{"idx": 7, "event_code": "DISC", "timestamp": "2026-08-12 00:00:00", "location": "Beira", "is_actual": 1, "description": "Import Discharged from Vessel", "container_number": "TGBU3890006"},
		{"idx": 8, "event_code": "GTOT", "timestamp": "2026-08-18 00:00:00", "location": "Beira", "is_actual": 1, "description": "Import to consignee", "container_number": "TGBU3890006"},
	]
	return {
		"status": "IN_TRANSIT",
		"reference_number": "SHP-TEST",
		"containers_table": [
			{"container_number": "MEDU5945450", "iso_code": "22G1", "size_type": "20SD", "status": "IN_TRANSIT"},
			{"container_number": "TGBU3890006", "iso_code": "22G1", "size_type": "20SD", "status": "IN_TRANSIT"},
		],
		"events_table": events,
		"voyage_plan_table": [
			{"origin": "Xiamen", "destination": "Singapore"},
			{"origin": "Singapore", "destination": "Beira"},
		],
		"locations_table": [
			{"name": "Xiamen", "country": "China"},
			{"name": "Singapore", "country": "Singapore"},
			{"name": "Beira", "country": "Mozambique"},
		],
	}


class TestLocationMatches(unittest.TestCase):
	def test_exact_and_partial_port_names(self):
		self.assertTrue(location_matches("Beira", "Beira"))
		self.assertTrue(location_matches("Beira, Mozambique", "Beira"))
		self.assertFalse(location_matches("Singapore", "Beira"))


class TestTraqoMultiContainerParsing(unittest.TestCase):
	def test_events_for_container_filters_by_container_number(self):
		events = _beira_bl_fixture()["events_table"]
		medu = _events_for_container(events, "MEDU5945450")
		self.assertEqual(len(medu), 4)
		self.assertTrue(all(e["container_number"] == "MEDU5945450" for e in medu))

	def test_shared_events_table_yields_per_container_dates(self):
		data = _beira_bl_fixture()
		route_data = {"pol": {"name": "Xiamen"}, "pod": {"name": "Beira"}}
		containers = _parse_containers(data, "BL", route_data)
		by_number = {row["container_number"]: row for row in containers}

		self.assertEqual(by_number["MEDU5945450"]["discharge_date"], "2026-08-10")
		self.assertEqual(by_number["MEDU5945450"]["gate_out_date"], "2026-08-19")
		self.assertEqual(by_number["TGBU3890006"]["discharge_date"], "2026-08-12")
		self.assertEqual(by_number["TGBU3890006"]["gate_out_date"], "2026-08-18")

	def test_merged_events_without_filter_picks_latest_across_containers(self):
		"""Document the old failure mode: all BL events assigned to every container."""
		data = _beira_bl_fixture()
		merged = parse_container_events(
			data["events_table"],
			pol_location_name="Xiamen",
			pod_location_name="Beira",
		)
		self.assertEqual(merged["discharge_date"], "2026-08-12")
		self.assertEqual(merged["gate_out_date"], "2026-08-19")

	def test_transshipment_disc_excluded_when_pod_known(self):
		events = [
			{"idx": 1, "event_code": "DISC", "timestamp": "2026-05-29 00:00:00", "location": "Singapore", "is_actual": 1, "container_number": "TEST0000001"},
			{"idx": 2, "event_code": "DISC", "timestamp": "2026-08-10 00:00:00", "location": "Beira", "is_actual": 1, "container_number": "TEST0000001"},
		]
		result = parse_container_events(events, pol_location_name="Xiamen", pod_location_name="Beira")
		self.assertEqual(result["discharge_date"], "2026-08-10")

	def test_export_gate_out_excluded_when_pol_known(self):
		events = [
			{"idx": 1, "event_code": "GTOT", "timestamp": "2026-05-13 00:00:00", "location": "Xiamen", "is_actual": 1, "description": "Empty to Shipper", "container_number": "TEST0000001"},
			{"idx": 2, "event_code": "GTOT", "timestamp": "2026-08-19 00:00:00", "location": "Beira", "is_actual": 1, "description": "Import to consignee", "container_number": "TEST0000001"},
		]
		result = parse_container_events(events, pol_location_name="Xiamen", pod_location_name="Beira")
		self.assertEqual(result["gate_out_date"], "2026-08-19")
