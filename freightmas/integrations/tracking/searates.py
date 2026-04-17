# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Searates tracking API service.

Fetches and parses container tracking data from the Searates API.
Returns structured data — does NOT write to any doctype.
"""

import json

import frappe
import requests


def get_settings():
	"""Return FreightMas Settings singleton, validating shipping tracker is enabled."""
	settings = frappe.get_single("FreightMas Settings")
	if not settings.enable_shipping_tracker:
		frappe.throw("Shipping Tracker is not enabled. Please enable it in FreightMas Settings > Shipping Tracker.")
	api_key = settings.get_password("shipping_tracker_api_key")
	if not api_key:
		frappe.throw("API Key is not configured in FreightMas Settings > Shipping Tracker.")
	return settings, api_key


def fetch_tracking(bl_number, tracking_type="BL", sealine=None):
	"""Call Searates tracking API and return parsed tracking data.

	Args:
		bl_number: The BL/container/booking number to track
		tracking_type: "BL", "CT", or "BK"
		sealine: Optional SCAC code for the shipping line

	Returns:
		dict with keys: metadata, route, vessel, containers, mappings
	"""
	_settings, api_key = get_settings()

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

	# Build lookup dictionaries for resolving IDs
	locations = {loc["id"]: loc for loc in (data.get("locations") or [])}
	facilities = {fac["id"]: fac for fac in (data.get("facilities") or [])}
	vessels = {v["id"]: v for v in (data.get("vessels") or [])}

	# Parse metadata
	metadata = data.get("metadata") or {}
	tracking_status = metadata.get("status", "")
	sealine_code = metadata.get("sealine", "")
	sealine_name = metadata.get("sealine_name", "")

	# Parse route
	route = data.get("route") or {}
	route_data = _parse_route(route, locations)

	# Parse first vessel
	vessel_list = data.get("vessels") or []
	vessel_data = {}
	if vessel_list:
		first_vessel = vessel_list[0]
		vessel_data = {
			"name": first_vessel.get("name", ""),
			"imo": str(first_vessel.get("imo", "")),
			"flag": first_vessel.get("flag", ""),
		}

	# Normalize containers — BL returns data.containers[], CT returns data.container (single)
	containers_raw = data.get("containers") or []
	if not containers_raw and data.get("container"):
		containers_raw = [data["container"]]

	# Parse containers and compute mappings
	containers = []
	last_voyage = ""
	for container in containers_raw:
		events = container.get("events") or []

		# Find latest event (highest order_id)
		latest_event = max(events, key=lambda e: e.get("order_id", 0)) if events else {}
		latest_loc = locations.get(latest_event.get("location")) or {}

		# Find discharge event for this container
		discharge_date = None
		for event in events:
			if event.get("event_code") == "DISC" and event.get("actual"):
				evt_date = _extract_date(event.get("date"))
				if evt_date and (not discharge_date or evt_date > discharge_date):
					discharge_date = evt_date

		containers.append({
			"container_number": container.get("number", ""),
			"iso_code": container.get("iso_code", ""),
			"size_type": container.get("size_type", ""),
			"status": container.get("status", ""),
			"latest_event_description": latest_event.get("description", ""),
			"latest_event_date": latest_event.get("date", ""),
			"latest_event_port": latest_loc.get("name", ""),
			"discharge_date": discharge_date,
		})

		# Track last voyage for vessel/voyage mapping
		for event in events:
			if event.get("voyage"):
				last_voyage = event["voyage"]

	# Compute Forwarding Job field mappings
	mappings = _compute_mappings(route_data, vessel_data, last_voyage)

	return {
		"metadata": {
			"status": tracking_status,
			"sealine_code": sealine_code,
			"sealine_name": sealine_name,
		},
		"route": route_data,
		"vessel": vessel_data,
		"containers": containers,
		"mappings": mappings,
	}


def _parse_route(route, locations):
	"""Parse route.pol and route.pod."""
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


def _compute_mappings(route_data, vessel_data, last_voyage):
	"""Compute Forwarding Job field values from tracking data."""
	# Vessel / Voyage
	vessel_name = vessel_data.get("name", "")
	if vessel_name and last_voyage:
		vessel_flight_no = f"{vessel_name} / {last_voyage}"
	elif vessel_name:
		vessel_flight_no = vessel_name
	else:
		vessel_flight_no = ""

	pol = route_data.get("pol") or {}
	pod = route_data.get("pod") or {}

	# ETD / ATD from POL date
	pol_date = _extract_date(pol.get("date"))
	etd = pol_date
	atd = pol_date if pol.get("actual") else None

	# ETA / ATA from POD date
	pod_date = _extract_date(pod.get("date"))
	eta = pod_date
	ata = pod_date if pod.get("actual") else None

	return {
		"vessel_flight_no": vessel_flight_no,
		"etd": etd,
		"atd": atd,
		"eta": eta,
		"ata": ata,
	}


def _extract_date(datetime_str):
	"""Extract the date portion (YYYY-MM-DD) from a datetime string."""
	if not datetime_str:
		return None
	return str(datetime_str)[:10] or None
