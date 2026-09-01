# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Shared tracking utilities and normalized output contract."""

import frappe


def get_tracking_settings():
	"""Return FreightMas Settings singleton, validating shipping tracker is enabled."""
	settings = frappe.get_single("FreightMas Settings")
	if not settings.enable_shipping_tracker:
		frappe.throw(
			"Shipping Tracker is not enabled. Please enable it in FreightMas Settings > Tracking & Integration."
		)
	api_key = settings.get_password("shipping_tracker_api_key")
	if not api_key:
		frappe.throw("API Key is not configured in FreightMas Settings > Tracking & Integration.")
	return settings, api_key


def get_tracking_provider():
	settings = frappe.get_single("FreightMas Settings")
	provider = frappe.db.get_single_value("FreightMas Settings", "tracking_provider")
	return (provider or settings.tracking_provider or "Searates").strip()


def resolve_sealine(sealine=None, shipping_line=None):
	"""Resolve a SCAC code from explicit sealine or a Shipping Line link."""
	if sealine:
		return sealine.strip().upper()

	if not shipping_line:
		return None

	scac = frappe.db.get_value("Shipping Line", shipping_line, "scac_code")
	return scac.strip().upper() if scac else None


def require_sealine_for_traqo(sealine, shipping_line):
	"""Traqo requires a carrier SCAC on every tracking request."""
	if get_tracking_provider() != "Traqo":
		return resolve_sealine(sealine, shipping_line)

	scac = resolve_sealine(sealine, shipping_line)
	if not scac:
		frappe.throw(
			"Shipping Line (with SCAC code) is required for Traqo tracking. "
			"Set the Shipping Line on the job before fetching."
		)
	return scac


def extract_date(datetime_str):
	"""Extract the date portion (YYYY-MM-DD) from a datetime string."""
	if not datetime_str:
		return None
	return str(datetime_str)[:10] or None


def _location_key(value):
	if value is None:
		return ""
	return str(value).strip().lower().split(",")[0].strip()


def location_matches(event_location, target_location):
	"""Return True when an event location corresponds to a POL/POD guard."""
	if target_location is None:
		return True
	if event_location is None:
		return False

	if isinstance(target_location, int) or isinstance(event_location, int):
		try:
			return int(event_location) == int(target_location)
		except (TypeError, ValueError):
			return event_location == target_location

	event_key = _location_key(event_location)
	target_key = _location_key(target_location)
	if not event_key or not target_key:
		return False
	return (
		event_key == target_key
		or event_key.startswith(f"{target_key} ")
		or target_key.startswith(f"{event_key} ")
	)


_TRANSSHIPMENT_DESC_KEYWORDS = ("transshipment", "trans-shipment", "trans shipment")


def _is_transshipment_description(description):
	desc = (description or "").lower()
	return any(kw in desc for kw in _TRANSSHIPMENT_DESC_KEYWORDS)


def _is_at_transshipment_port(evt_location, transshipment_location_names):
	for port_name in transshipment_location_names or []:
		if location_matches(evt_location, port_name):
			return True
	return False


def parse_container_events(
	events,
	locations=None,
	pol_location_id=None,
	pod_location_id=None,
	pol_location_name=None,
	pod_location_name=None,
	transshipment_location_names=None,
):
	"""Parse milestone events into container-level dates and latest event.

	Args:
		events: list of dicts with event_code, date/timestamp, actual/is_actual, location, description, order_id/idx
		locations: optional id->location dict (SeaRates) or unused when events carry location names
		pol_location_id: SeaRates POL location id guard
		pod_location_id: SeaRates POD location id guard
		pol_location_name: Traqo POL port name guard (export-side gate-outs)
		pod_location_name: Traqo POD port name guard (import discharge/gate-out)
		transshipment_location_names: intermediate ports where DISC must be ignored
	"""
	locations = locations or {}
	today = frappe.utils.nowdate()

	normalized_events = []
	for event in events or []:
		evt_location = event.get("location")
		if isinstance(evt_location, int) and locations:
			loc = locations.get(evt_location) or {}
			location_name = loc.get("name", "")
		else:
			location_name = evt_location or ""

		normalized_events.append({
			"event_code": event.get("event_code", ""),
			"description": event.get("description", ""),
			"date": event.get("date") or event.get("timestamp") or "",
			"actual": bool(event.get("actual") if "actual" in event else event.get("is_actual")),
			"location": evt_location,
			"location_name": location_name,
			"order_id": event.get("order_id", event.get("idx", 0)),
			"voyage": event.get("voyage", ""),
		})

	latest_event = max(normalized_events, key=lambda e: e.get("order_id", 0)) if normalized_events else {}
	latest_loc_name = latest_event.get("location_name", "")

	discharge_date = None
	gate_out_date = None
	empty_return_date = None
	pod_guard = pod_location_id if pod_location_id is not None else pod_location_name
	pol_guard = pol_location_id if pol_location_id is not None else pol_location_name

	def _is_at_pol(evt_location):
		if pol_location_id is not None:
			return evt_location == pol_location_id
		if pol_location_name:
			return location_matches(evt_location, pol_location_name)
		return False

	def _is_at_pod(evt_location):
		if pod_location_id is not None:
			return evt_location == pod_location_id
		if pod_location_name:
			return location_matches(evt_location, pod_location_name)
		return False

	def _apply_event_date(code, evt_date, evt_location, description=""):
		nonlocal discharge_date, gate_out_date, empty_return_date
		if evt_date > today:
			return
		if code == "DISC":
			if _is_transshipment_description(description):
				return
			if _is_at_transshipment_port(evt_location, transshipment_location_names):
				return
			if pod_guard is not None and not _is_at_pod(evt_location):
				return
			if not discharge_date or evt_date > discharge_date:
				discharge_date = evt_date
		elif code in ("GOUT", "AVPU", "DLVR", "GTOT"):
			if _is_at_pol(evt_location):
				return
			if pod_guard is not None and not _is_at_pod(evt_location):
				return
			if not gate_out_date or evt_date > gate_out_date:
				gate_out_date = evt_date
		elif code in ("IRTN", "EMRT", "RTRN"):
			if _is_at_pol(evt_location):
				return
			if not empty_return_date or evt_date > empty_return_date:
				empty_return_date = evt_date

	for actual_only in (True, False):
		if discharge_date and gate_out_date and empty_return_date:
			break
		for event in normalized_events:
			if event.get("actual") != actual_only:
				continue
			evt_date = extract_date(event.get("date"))
			if evt_date:
				_apply_event_date(
					event.get("event_code"),
					evt_date,
					event.get("location"),
					event.get("description", ""),
				)

	_gate_out_keywords = (
		"gate out", "gate-out", "pickup", "picked up",
		"delivery", "delivered", "available for pickup",
		"to consignee", "import to consignee",
	)
	_empty_return_keywords = (
		"empty return", "empty received", "returned empty",
		"empty gate in", "empty restitution", "empty drop",
		"end import cycle",
	)
	if not gate_out_date or not empty_return_date:
		for event in sorted(normalized_events, key=lambda e: e.get("order_id", 0), reverse=True):
			evt_date = extract_date(event.get("date"))
			if not evt_date or evt_date > today:
				continue
			if _is_at_pol(event.get("location")):
				continue
			if pod_guard is not None and not _is_at_pod(event.get("location")):
				continue
			desc = (event.get("description") or "").lower()
			if not gate_out_date and any(kw in desc for kw in _gate_out_keywords):
				gate_out_date = evt_date
			if not empty_return_date and any(kw in desc for kw in _empty_return_keywords):
				empty_return_date = evt_date
			if gate_out_date and empty_return_date:
				break

	last_voyage = ""
	for event in normalized_events:
		if event.get("voyage"):
			last_voyage = event["voyage"]

	return {
		"latest_event_code": latest_event.get("event_code", ""),
		"latest_event_actual": bool(latest_event.get("actual")),
		"latest_event_description": latest_event.get("description", ""),
		"latest_event_date": latest_event.get("date", ""),
		"latest_event_port": latest_loc_name,
		"discharge_date": discharge_date,
		"gate_out_date": gate_out_date,
		"empty_return_date": empty_return_date,
		"last_voyage": last_voyage,
	}


def compute_mappings(route_data, vessel_data, last_voyage):
	"""Compute job field values from normalized route and vessel data."""
	vessel_name = vessel_data.get("name", "")
	if vessel_name and last_voyage:
		vessel_flight_no = f"{vessel_name} / {last_voyage}"
	elif vessel_name:
		vessel_flight_no = vessel_name
	else:
		vessel_flight_no = ""

	pol = route_data.get("pol") or {}
	pod = route_data.get("pod") or {}

	pol_date = extract_date(pol.get("date"))
	pod_date = extract_date(pod.get("date"))

	return {
		"vessel_flight_no": vessel_flight_no,
		"etd": pol_date,
		"atd": pol_date if pol.get("actual") else None,
		"eta": pod_date,
		"ata": pod_date if pod.get("actual") else None,
	}


def empty_tracking_result():
	return {
		"metadata": {"status": "", "sealine_code": "", "sealine_name": ""},
		"route": {"pol": {}, "pod": {}},
		"vessel": {},
		"containers": [],
		"mappings": compute_mappings({}, {}, ""),
		"provider_extras": {},
	}
