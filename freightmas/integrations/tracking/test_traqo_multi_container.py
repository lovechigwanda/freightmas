# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Regression tests for Traqo multi-container BL event parsing."""

import unittest

from freightmas.integrations.tracking.base import location_matches, parse_container_events
from freightmas.integrations.tracking.traqo import (
	_events_for_container,
	_parse_containers,
	_parse_route,
	_parse_traqo_response,
)


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


def _untagged_single_container_fixture():
	"""Sandbox-style CT payload: shipment-level events without container_number tags."""
	events = [
		{"idx": 1, "event_code": "GTIN", "timestamp": "2026-07-08 13:09:29", "location": "Port of Long Beach", "is_actual": 1, "description": "Gate in full"},
		{"idx": 2, "event_code": "LOAD", "timestamp": "2026-07-13 02:35:53", "location": "Port of Long Beach", "is_actual": 1, "description": "Loaded on vessel"},
		{"idx": 3, "event_code": "GTOT", "timestamp": "2026-09-06 13:09:29", "location": "Port of Klaipeda", "is_actual": 0, "description": "Gate out"},
	]
	return {
		"status": "DELIVERED",
		"reference_number": "MRSU6859427",
		"container_summary": "1×40HC",
		"containers_table": [
			{
				"container_number": "MRSU6859427",
				"iso_code": "45G1",
				"size_type": "40HC",
				"container_description": "40ft High Cube General Purpose",
				"status": "DELIVERED",
			},
		],
		"events_table": events,
		"voyage_plan_table": [
			{"origin": "Port of Long Beach", "destination": "Port of Klaipeda"},
		],
		"locations_table": [
			{"name": "Port of Long Beach", "country": "United States"},
			{"name": "Port of Klaipeda", "country": "Lithuania"},
		],
	}


def _colombo_beira_in_transit_fixture():
	"""Modelled on FWJB-00286-26: Fos sur mer → Beira via Colombo, still in transit."""
	events = [
		{"idx": 1, "event_code": "DEPA", "timestamp": "2026-07-10 00:00:00", "location": "Fos sur mer", "is_actual": 1, "description": "Vessel departed", "container_number": "LHV4047029"},
		{"idx": 2, "event_code": "DISC", "timestamp": "2026-07-23 00:00:00", "location": "Port of Colombo", "is_actual": 1, "description": "Full Transshipment Discharged", "container_number": "LHV4047029"},
		{"idx": 3, "event_code": "LOAD", "timestamp": "2026-08-28 00:00:00", "location": "Port of Colombo", "is_actual": 1, "description": "Loaded on vessel", "container_number": "LHV4047029"},
	]
	return {
		"status": "IN_TRANSIT",
		"origin": "Fos sur mer, France",
		"destination": "Beira, Mozambique",
		"eta": "2026-09-04 00:00:00",
		"reference_number": "SHP-78004",
		"containers_table": [
			{"container_number": "LHV4047029", "iso_code": "22G1", "size_type": "20SD", "status": "IN_TRANSIT"},
		],
		"events_table": events,
		"voyage_plan_table": [
			{"origin": "Fos sur mer", "destination": "Port of Colombo", "arrival_actual": True},
		],
		"locations_table": [
			{"name": "Fos sur mer", "country": "France"},
			{"name": "Port of Colombo", "country": "Sri Lanka"},
			{"name": "Beira", "country": "Mozambique"},
		],
	}


class TestMatchContainerType(unittest.TestCase):
	def test_match_by_iso_code(self):
		from freightmas.utils.master_data_sync import match_container_type

		self.assertEqual(match_container_type("45G1"), "40HC")

	def test_match_by_size_type_when_iso_missing(self):
		from freightmas.utils.master_data_sync import match_container_type

		self.assertEqual(match_container_type(None, "40HC"), "40HC")

	def test_iso_code_takes_priority_over_size_type(self):
		from freightmas.utils.master_data_sync import match_container_type

		self.assertEqual(match_container_type("45G1", "20SD"), "40HC")


class TestLocationMatches(unittest.TestCase):
	def test_exact_and_partial_port_names(self):
		self.assertTrue(location_matches("Beira", "Beira"))
		self.assertTrue(location_matches("Beira, Mozambique", "Beira"))
		self.assertFalse(location_matches("Singapore", "Beira"))


class TestTraqoMultiContainerParsing(unittest.TestCase):
	def test_events_for_container_returns_shared_timeline_when_untagged(self):
		events = _untagged_single_container_fixture()["events_table"]
		self.assertEqual(len(_events_for_container(events, "MRSU6859427")), len(events))

	def test_untagged_events_populate_latest_event_code(self):
		parsed = _parse_traqo_response(_untagged_single_container_fixture(), "CT")
		container = parsed["containers"][0]
		self.assertEqual(container["latest_event_code"], "GTOT")
		self.assertEqual(container["iso_code"], "45G1")
		self.assertEqual(container["size_type"], "40HC")
		self.assertEqual(container["container_description"], "40ft High Cube General Purpose")
		self.assertEqual(parsed["provider_extras"]["container_summary"], "1×40HC")

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

	def test_transshipment_disc_excluded_by_description(self):
		events = [
			{"idx": 1, "event_code": "DISC", "timestamp": "2026-07-23 00:00:00", "location": "Beira", "is_actual": 1, "description": "Full Transshipment Discharged"},
		]
		result = parse_container_events(events, pod_location_name="Beira")
		self.assertIsNone(result["discharge_date"])

	def test_transshipment_disc_excluded_by_port_list(self):
		events = [
			{"idx": 1, "event_code": "DISC", "timestamp": "2026-07-23 00:00:00", "location": "Port of Colombo", "is_actual": 1, "description": "Discharged"},
		]
		result = parse_container_events(
			events,
			pod_location_name="Beira",
			transshipment_location_names=["Port of Colombo"],
		)
		self.assertIsNone(result["discharge_date"])


class TestColomboTransshipmentRouteParsing(unittest.TestCase):
	def test_parse_route_uses_destination_as_pod_not_last_voyage_leg(self):
		data = _colombo_beira_in_transit_fixture()
		route = _parse_route(data)
		self.assertEqual(route["pod"]["name"], "Beira")
		self.assertIn("Port of Colombo", route["transshipment_ports"])
		self.assertFalse(route["pod"]["actual"])

	def test_in_transit_colombo_transshipment_yields_no_discharge_date(self):
		data = _colombo_beira_in_transit_fixture()
		parsed = _parse_traqo_response(data, "BL")
		container = parsed["containers"][0]
		self.assertEqual(container["container_number"], "LHV4047029")
		self.assertIsNone(container["discharge_date"])
		self.assertIsNone(container["gate_out_date"])
		self.assertEqual(parsed["route"]["pod"]["name"], "Beira")
		self.assertIsNone(parsed["mappings"]["ata"])
