# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Validate Traqo sandbox responses and FreightMas parser output.

Run (no API key required):
    bench --site <site> execute freightmas.integrations.tracking.test_traqo_sandbox.run

Optional live check with your configured Traqo key:
    bench --site <site> execute freightmas.integrations.tracking.test_traqo_sandbox.run --kwargs '{"live": true}'
"""

import json

import frappe
import requests

from freightmas.integrations.tracking.traqo import _parse_traqo_response, fetch_tracking

SANDBOX_BASE = "https://traqocontainer.com/api/v1/sandbox"

SANDBOX_CASES = (
	{
		"label": "Container (Maersk)",
		"tracking_type": "CT",
		"path": "/container/MRSU6859427",
		"sealine": "MAEU",
		"expected_reference": "MRSU6859427",
		"expected_sealine": "MAEU",
	},
	{
		"label": "Bill of Lading (CMA CGM)",
		"tracking_type": "BL",
		"path": "/bl/SHZ8037930",
		"sealine": "CMDU",
		"expected_reference": "SHZ8037930",
		"expected_sealine": None,
	},
)

REQUIRED_TOP_LEVEL_KEYS = ("metadata", "route", "vessel", "containers", "mappings", "provider_extras")
REQUIRED_CONTAINER_KEYS = (
	"container_number",
	"iso_code",
	"size_type",
	"container_description",
	"latest_event_code",
	"latest_event_description",
	"latest_event_date",
	"discharge_date",
	"gate_out_date",
	"empty_return_date",
)


def run(live=False):
	"""Entry point for bench execute."""
	results = []
	passed = 0
	failed = 0

	print("\n=== Traqo Tracking Sandbox Validation ===\n")

	for case in SANDBOX_CASES:
		ok, detail = _run_sandbox_case(case)
		results.append((case["label"], ok, detail))
		if ok:
			passed += 1
			print(f"PASS  {case['label']}")
			print(f"      {detail}\n")
		else:
			failed += 1
			print(f"FAIL  {case['label']}")
			print(f"      {detail}\n")

	if live:
		print("--- Live API check (uses FreightMas Settings API key) ---\n")
		for case in SANDBOX_CASES:
			ok, detail = _run_live_case(case)
			label = f"{case['label']} [live]"
			results.append((label, ok, detail))
			if ok:
				passed += 1
				print(f"PASS  {label}")
				print(f"      {detail}\n")
			else:
				failed += 1
				print(f"FAIL  {label}")
				print(f"      {detail}\n")

	print("=== Summary ===")
	print(f"Passed: {passed}")
	print(f"Failed: {failed}")
	print(f"Total:  {passed + failed}\n")

	if failed:
		frappe.throw(f"Traqo sandbox validation failed ({failed} case(s)). See output above.")

	return {
		"passed": passed,
		"failed": failed,
		"results": [{"label": label, "ok": ok, "detail": detail} for label, ok, detail in results],
	}


def _run_sandbox_case(case):
	try:
		payload = _fetch_sandbox(case["path"], case["sealine"])
		data = payload.get("data") or {}
		if not data:
			return False, "Sandbox response missing data object"

		parsed = _parse_traqo_response(data, case["tracking_type"])
		errors = _validate_parsed_result(parsed, case)
		if errors:
			return False, "; ".join(errors)

		summary = _format_summary(parsed, sandbox=True)
		return True, summary
	except Exception as exc:
		return False, str(exc)


def _run_live_case(case):
	try:
		settings = frappe.get_single("FreightMas Settings")
		if not settings.enable_shipping_tracker:
			return False, "Shipping Tracker is disabled in FreightMas Settings"
		if (settings.tracking_provider or "") != "Traqo":
			return False, "Tracking provider is not set to Traqo"
		if not settings.get_password("shipping_tracker_api_key"):
			return False, "Traqo API key is not configured"

		number = case["expected_reference"]
		parsed = fetch_tracking(number, tracking_type=case["tracking_type"], sealine=case["sealine"])
		errors = _validate_parsed_result(parsed, case)
		if errors:
			return False, "; ".join(errors)

		return True, _format_summary(parsed, sandbox=False)
	except Exception as exc:
		return False, str(exc)


def _fetch_sandbox(path, sealine):
	url = f"{SANDBOX_BASE}{path}"
	resp = requests.get(url, params={"sealine": sealine}, timeout=60)
	resp.raise_for_status()
	payload = resp.json()
	if not payload.get("success"):
		raise frappe.ValidationError(f"Sandbox API returned success=false: {json.dumps(payload)[:300]}")
	return payload


def _validate_parsed_result(parsed, case):
	errors = []

	for key in REQUIRED_TOP_LEVEL_KEYS:
		if key not in parsed:
			errors.append(f"missing top-level key: {key}")

	metadata = parsed.get("metadata") or {}
	expected_sealine = case.get("expected_sealine")
	if expected_sealine is not None:
		if metadata.get("sealine_code") != expected_sealine:
			errors.append(
				f"sealine_code expected {expected_sealine!r}, got {metadata.get('sealine_code')!r}"
			)
	elif not metadata.get("sealine_code"):
		errors.append("metadata.sealine_code is empty")
	if not metadata.get("status"):
		errors.append("metadata.status is empty")

	containers = parsed.get("containers") or []
	if not containers:
		errors.append("containers list is empty")
	else:
		first = containers[0]
		for key in REQUIRED_CONTAINER_KEYS:
			if key not in first:
				errors.append(f"container missing key: {key}")
		if not first.get("container_number"):
			errors.append("container_number is empty")
		if not first.get("latest_event_code"):
			errors.append("latest_event_code is empty (events_table may not have parsed)")

	route = parsed.get("route") or {}
	for leg in ("pol", "pod"):
		if leg not in route:
			errors.append(f"route missing {leg}")

	mappings = parsed.get("mappings") or {}
	for key in ("vessel_flight_no", "etd", "atd", "eta", "ata"):
		if key not in mappings:
			errors.append(f"mappings missing key: {key}")

	extras = parsed.get("provider_extras") or {}
	if not extras.get("traqo_shipment_id"):
		errors.append("provider_extras.traqo_shipment_id is empty")
	if "container_summary" not in extras:
		errors.append("provider_extras.container_summary is missing")

	return errors


def _format_summary(parsed, sandbox=False):
	metadata = parsed.get("metadata") or {}
	containers = parsed.get("containers") or []
	first = containers[0] if containers else {}
	mappings = parsed.get("mappings") or {}
	extras = parsed.get("provider_extras") or {}
	mode = "sandbox" if sandbox else "live"

	return (
		f"[{mode}] status={metadata.get('status')} | "
		f"containers={len(containers)} | "
		f"latest_event={first.get('latest_event_code')} | "
		f"iso={first.get('iso_code') or '-'} | "
		f"size={first.get('size_type') or '-'} | "
		f"summary={extras.get('container_summary') or '-'} | "
		f"vessel={mappings.get('vessel_flight_no') or '-'} | "
		f"eta={mappings.get('eta') or '-'}"
	)
