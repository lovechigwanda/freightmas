# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Searates tracking API service.

Fetches and parses container tracking data from the Searates API.
Returns structured data — does NOT write to any doctype.
"""

import json

import frappe
import requests

from freightmas.integrations.tracking.base import (
	compute_mappings,
	extract_date,
	get_tracking_settings,
	parse_container_events,
)

# Backwards-compatible alias used in patch comments.
_extract_date = extract_date


def fetch_tracking(bl_number, tracking_type="BL", sealine=None):
	"""Call Searates tracking API and return parsed tracking data."""
	_settings, api_key = get_tracking_settings()

	params = {
		"api_key": api_key,
		"number": bl_number.strip(),
		"type": tracking_type,
	}
	if sealine:
		params["sealine"] = sealine.strip()

	try:
		resp = requests.get(
			"https://tracking.searates.com/tracking",
			params=params,
			timeout=60,
		)
		resp.raise_for_status()
		result = resp.json()
	except requests.exceptions.Timeout:
		frappe.throw("Searates API request timed out. Please try again.")
	except requests.exceptions.RequestException as e:
		frappe.throw(f"Searates API request failed: {e}")
	except json.JSONDecodeError:
		frappe.throw("Invalid JSON response from Searates API")

	status = result.get("status")
	if status == "error":
		msg = result.get("message", "Unknown error")
		frappe.throw(f"Searates API error: {msg}")

	data = result.get("data")
	if not data:
		frappe.throw("No tracking data returned from Searates API")

	locations = {loc["id"]: loc for loc in (data.get("locations") or [])}
	route = data.get("route") or {}
	route_data = _parse_route(route, locations)

	pol_location_id = (route.get("pol") or {}).get("location")
	pod_location_id = (route.get("pod") or {}).get("location")

	vessel_list = data.get("vessels") or []
	vessel_data = {}
	if vessel_list:
		first_vessel = vessel_list[0]
		vessel_data = {
			"name": first_vessel.get("name", ""),
			"imo": str(first_vessel.get("imo", "")),
			"flag": first_vessel.get("flag", ""),
		}

	containers_raw = data.get("containers") or []
	if not containers_raw and data.get("container"):
		containers_raw = [data["container"]]

	containers = []
	last_voyage = ""
	for container in containers_raw:
		events = container.get("events") or []
		event_data = parse_container_events(
			events,
			locations=locations,
			pol_location_id=pol_location_id,
			pod_location_id=pod_location_id,
		)
		if event_data.get("last_voyage"):
			last_voyage = event_data["last_voyage"]

		containers.append({
			"container_number": container.get("number", ""),
			"iso_code": container.get("iso_code", ""),
			"size_type": container.get("size_type", ""),
			"status": container.get("status", ""),
			**{k: event_data[k] for k in (
				"latest_event_code", "latest_event_actual", "latest_event_description",
				"latest_event_date", "latest_event_port", "discharge_date",
				"gate_out_date", "empty_return_date",
			)},
		})

	metadata = data.get("metadata") or {}
	mappings = compute_mappings(route_data, vessel_data, last_voyage)

	return {
		"metadata": {
			"status": metadata.get("status", ""),
			"sealine_code": metadata.get("sealine", ""),
			"sealine_name": metadata.get("sealine_name", ""),
		},
		"route": route_data,
		"vessel": vessel_data,
		"containers": containers,
		"mappings": mappings,
		"provider_extras": {},
	}


def _parse_route(route, locations):
	pol = route.get("pol") or {}
	pod = route.get("pod") or {}

	pol_loc = locations.get(pol.get("location")) or {}
	pod_loc = locations.get(pod.get("location")) or {}

	return {
		"pol": {
			"name": pol_loc.get("name", ""),
			"country": pol_loc.get("country", ""),
			"country_code": pol_loc.get("country_code", ""),
			"locode": pol_loc.get("locode", ""),
			"date": pol.get("date", ""),
			"actual": bool(pol.get("actual")),
		},
		"pod": {
			"name": pod_loc.get("name", ""),
			"country": pod_loc.get("country", ""),
			"country_code": pod_loc.get("country_code", ""),
			"locode": pod_loc.get("locode", ""),
			"date": pod.get("date", ""),
			"actual": bool(pod.get("actual")),
		},
	}
