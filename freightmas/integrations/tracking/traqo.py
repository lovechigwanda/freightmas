# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Traqo container tracking API service."""

import json

import frappe
import requests

from freightmas.integrations.tracking.base import (
	compute_mappings,
	extract_date,
	get_tracking_settings,
	parse_container_events,
)

BASE_URL = "https://traqocontainer.com/api/v1"


def _headers(api_key):
	return {"Authorization": f"Bearer {api_key}"}


def _request(api_key, method, path, **kwargs):
	url = f"{BASE_URL}{path}"
	try:
		resp = requests.request(method, url, headers=_headers(api_key), timeout=60, **kwargs)
	except requests.exceptions.Timeout:
		frappe.throw("Traqo API request timed out. Please try again.")
	except requests.exceptions.RequestException as e:
		frappe.throw(f"Traqo API request failed: {e}")

	try:
		payload = resp.json()
	except json.JSONDecodeError:
		frappe.throw("Invalid JSON response from Traqo API")

	if resp.status_code == 429:
		retry_after = resp.headers.get("Retry-After") or payload.get("data", {}).get("retryAfter", 60)
		frappe.throw(f"Traqo rate limit exceeded. Retry after {retry_after}s.")

	if resp.status_code == 402:
		error_type = (payload.get("data") or {}).get("error", "")
		if error_type == "shipment_limit_reached":
			frappe.throw("Traqo shipment limit reached. Untrack completed jobs or upgrade your plan.")
		frappe.throw(payload.get("statusMessage") or "Traqo payment or billing issue.")

	if resp.status_code >= 400:
		msg = payload.get("statusMessage") or payload.get("message") or resp.text
		frappe.throw(f"Traqo API error ({resp.status_code}): {msg}")

	if payload.get("success") is False:
		frappe.throw(payload.get("message") or payload.get("statusMessage") or "Traqo API request failed")

	return payload


def fetch_tracking(number, tracking_type="BL", sealine=None, traqo_shipment_id=None):
	"""Call Traqo live tracking API and return normalized tracking data."""
	_settings, api_key = get_tracking_settings()
	if not sealine:
		frappe.throw("Carrier SCAC (sealine) is required for Traqo tracking.")

	tracking_type = (tracking_type or "BL").upper()
	if tracking_type == "BK":
		frappe.throw("Traqo does not support booking (BK) tracking. Use BL or CT.")

	path_number = number.strip()
	if tracking_type == "CT":
		path = f"/container/{path_number}"
	else:
		path = f"/bl/{path_number}"

	result = _request(api_key, "GET", path, params={"sealine": sealine.strip().upper()})
	data = result.get("data") or {}
	if not data:
		frappe.throw("No tracking data returned from Traqo API")

	return _parse_traqo_response(data, tracking_type)


def refresh_tracking(traqo_shipment_id, number, tracking_type="BL", sealine=None):
	"""Re-fetch an already-tracked shipment from Traqo (does not consume a slot)."""
	return fetch_tracking(number, tracking_type=tracking_type, sealine=sealine, traqo_shipment_id=traqo_shipment_id)


def fetch_stored_summary(traqo_shipment_id):
	"""Cheap read of stored Traqo shipment data (no carrier re-fetch)."""
	_settings, api_key = get_tracking_settings()
	if not traqo_shipment_id:
		return None

	result = _request(api_key, "GET", f"/shipments/{traqo_shipment_id.strip()}")
	return result.get("data")


def list_updated_shipments(updated_since):
	"""Return reference numbers changed since the given ISO timestamp."""
	_settings, api_key = get_tracking_settings()
	if not updated_since:
		return None

	result = _request(
		api_key,
		"GET",
		"/shipments",
		params={"updated_since": updated_since},
	)
	return [row.get("reference_number") for row in (result.get("data") or []) if row.get("reference_number")]


def untrack_shipment(traqo_shipment_id):
	"""Stop tracking a shipment in Traqo and free the slot."""
	if not traqo_shipment_id:
		return False

	_settings, api_key = get_tracking_settings()
	try:
		_request(api_key, "DELETE", f"/shipments/{traqo_shipment_id.strip()}")
		return True
	except frappe.ValidationError:
		frappe.log_error(title=f"Traqo untrack failed: {traqo_shipment_id}")
		return False


def _parse_traqo_response(data, tracking_type):
	metadata = {
		"status": data.get("status", ""),
		"sealine_code": data.get("sealine", ""),
		"sealine_name": data.get("sealine_name", ""),
	}

	route_data = _parse_route(data)
	vessel_data = _parse_vessel(data)
	containers = _parse_containers(data, tracking_type, route_data)

	last_voyage = ""
	for ct in containers:
		for event in data.get("events_table") or []:
			if event.get("voyage"):
				last_voyage = event["voyage"]
				break
		if last_voyage:
			break

	mappings = compute_mappings(route_data, vessel_data, last_voyage)

	predictive = data.get("predictive_eta") or {}
	predictive_eta = predictive.get("p50") or predictive.get("p80")

	provider_extras = {
		"traqo_shipment_id": data.get("reference_number") or data.get("name"),
		"tracking_public_url": data.get("shipment_public_url"),
		"predictive_eta": extract_date(predictive_eta),
		"eta_reliable": data.get("eta_reliable"),
		"eta_warning": data.get("eta_warning"),
		"is_delayed": bool(data.get("is_delayed")),
		"demurrage_risk": data.get("demurrage_risk"),
		"last_synced_at": data.get("last_synced_at"),
		"eta_history": _parse_eta_history(data.get("eta_history_table") or []),
		"vessel_imo": vessel_data.get("imo"),
		"vessel_mmsi": vessel_data.get("mmsi"),
	}

	if mappings.get("eta") and provider_extras.get("eta_reliable") is False and provider_extras.get("predictive_eta"):
		mappings["eta"] = provider_extras["predictive_eta"]

	return {
		"metadata": metadata,
		"route": route_data,
		"vessel": vessel_data,
		"containers": containers,
		"mappings": mappings,
		"provider_extras": provider_extras,
	}


def _location_key(value):
	if value is None:
		return ""
	return str(value).strip().lower()


def _parse_route(data):
	locations_by_name = {}
	for loc in data.get("locations_table") or []:
		key = _location_key(loc.get("name") or loc.get("location"))
		if key:
			locations_by_name[key] = loc

	voyage_plan = data.get("voyage_plan_table") or []
	pol = _empty_route_leg()
	pod = _empty_route_leg()

	if voyage_plan:
		first = voyage_plan[0]
		last = voyage_plan[-1]
		pol = _route_leg_from_voyage(first, locations_by_name, is_pol=True)
		pod = _route_leg_from_voyage(last, locations_by_name, is_pol=False)
	else:
		pol_name = (data.get("origin") or "").split(",")[0].strip()
		pod_name = (data.get("destination") or "").split(",")[0].strip()
		pol = _route_leg_from_name(pol_name, locations_by_name)
		pod = _route_leg_from_name(pod_name, locations_by_name)
		pod["date"] = data.get("eta") or ""
		pod["actual"] = False

		for event in data.get("events_table") or []:
			code = event.get("event_code")
			if code in ("GTIN", "LOAD", "DEPA") and not pol.get("date"):
				pol["date"] = event.get("timestamp") or ""
				pol["actual"] = bool(event.get("is_actual"))
				if event.get("location"):
					pol["name"] = str(event.get("location"))
			if code in ("ARRI", "DISC") and not pod.get("date"):
				pod["date"] = event.get("timestamp") or ""
				pod["actual"] = bool(event.get("is_actual"))
				if event.get("location"):
					pod["name"] = str(event.get("location"))

	return {"pol": pol, "pod": pod}


def _empty_route_leg():
	return {
		"name": "",
		"country": "",
		"country_code": "",
		"locode": "",
		"date": "",
		"actual": False,
	}


def _route_leg_from_voyage(leg, locations_by_name, is_pol=True):
	name = ""
	if is_pol:
		name = leg.get("origin") or leg.get("pol") or leg.get("from") or ""
		date = leg.get("departure_date") or leg.get("atd") or leg.get("etd") or ""
		actual = bool(leg.get("atd") or leg.get("departure_actual"))
	else:
		name = leg.get("destination") or leg.get("pod") or leg.get("to") or ""
		date = leg.get("arrival_date") or leg.get("ata") or leg.get("eta") or ""
		actual = bool(leg.get("ata") or leg.get("arrival_actual"))

	loc = locations_by_name.get(_location_key(name), {})
	return {
		"name": str(name or loc.get("name") or ""),
		"country": loc.get("country", ""),
		"country_code": loc.get("country_code") or loc.get("country_iso") or "",
		"locode": loc.get("locode") or loc.get("unlocode") or "",
		"date": date,
		"actual": actual,
	}


def _route_leg_from_name(name, locations_by_name):
	loc = locations_by_name.get(_location_key(name), {})
	return {
		"name": str(name or loc.get("name") or ""),
		"country": loc.get("country", ""),
		"country_code": loc.get("country_code") or loc.get("country_iso") or "",
		"locode": loc.get("locode") or loc.get("unlocode") or "",
		"date": "",
		"actual": False,
	}


def _parse_vessel(data):
	vessels = data.get("vessels_table") or []
	current = next((v for v in vessels if v.get("is_current")), None) or (vessels[0] if vessels else None)
	if not current:
		return {}

	return {
		"name": current.get("vessel") or current.get("name") or "",
		"imo": str(current.get("imo") or ""),
		"mmsi": str(current.get("mmsi") or ""),
		"flag": current.get("flag", ""),
	}


def _parse_containers(data, tracking_type, route_data=None):
	events = data.get("events_table") or []
	containers_raw = data.get("containers_table") or []
	route_data = route_data or {}
	pol_name = (route_data.get("pol") or {}).get("name") or None
	pod_name = (route_data.get("pod") or {}).get("name") or None

	if not containers_raw:
		ref = data.get("reference_number", "")
		if tracking_type == "CT" and ref:
			containers_raw = [{"container_number": ref, "iso_code": "", "size_type": "", "status": data.get("status", "")}]
		elif ref:
			containers_raw = [{"container_number": ref, "iso_code": "", "size_type": "", "status": data.get("status", "")}]

	parsed = []
	for container in containers_raw:
		container_number = _container_number(container)
		container_events = container.get("events")
		if not container_events:
			container_events = _events_for_container(events, container_number)

		event_data = parse_container_events(
			container_events,
			pol_location_name=pol_name,
			pod_location_name=pod_name,
		)
		status = container.get("status") or data.get("status") or ""
		parsed.append({
			"container_number": container_number,
			"iso_code": container.get("iso_code") or container.get("iso") or "",
			"size_type": container.get("size_type") or container.get("type") or "",
			"status": status,
			**{k: event_data[k] for k in (
				"latest_event_code", "latest_event_actual", "latest_event_description",
				"latest_event_date", "latest_event_port", "discharge_date",
				"gate_out_date", "empty_return_date",
			)},
		})

	return parsed


def _container_number(container):
	return (
		container.get("container_number")
		or container.get("number")
		or container.get("container")
		or ""
	).strip()


def _event_container_number(event):
	for key in ("container_number", "container", "equipment_number", "container_no"):
		value = event.get(key)
		if value:
			return str(value).strip()
	return ""


def _events_for_container(events, container_number):
	if not container_number:
		return events
	return [event for event in events if _event_container_number(event) == container_number]


def _parse_eta_history(rows):
	history = []
	for row in rows:
		history.append({
			"eta": extract_date(row.get("eta") or row.get("new_eta")),
			"previous_eta": extract_date(row.get("previous_eta") or row.get("old_eta")),
			"recorded_at": row.get("recorded_at") or row.get("timestamp") or row.get("created_at"),
			"source": row.get("source", ""),
		})
	return history
