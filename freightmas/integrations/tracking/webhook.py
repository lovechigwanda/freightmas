# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Traqo webhook receiver."""

import hashlib
import hmac
import json
import time

import frappe

from freightmas.integrations.tracking.base import get_tracking_provider


@frappe.whitelist(allow_guest=True, methods=["POST"])
def receive():
	"""Receive Traqo webhook events and queue job refreshes."""
	if frappe.request.method != "POST":
		frappe.throw("Method not allowed", frappe.PermissionError)

	if get_tracking_provider() != "Traqo":
		frappe.response.http_status_code = 404
		return {"ok": False, "error": "Traqo is not the active tracking provider"}

	raw_body = frappe.request.get_data(as_text=True) or ""
	_signature_header = frappe.get_request_header("X-Traqo-Signature") or ""
	delivery_id = frappe.get_request_header("X-Traqo-Delivery") or ""
	event_name = frappe.get_request_header("X-Traqo-Event") or ""

	if not _verify_signature(raw_body, _signature_header):
		frappe.response.http_status_code = 400
		return {"ok": False, "error": "Invalid signature"}

	try:
		payload = json.loads(raw_body)
	except json.JSONDecodeError:
		frappe.response.http_status_code = 400
		return {"ok": False, "error": "Invalid JSON"}

	event = payload.get("event") or event_name
	data = payload.get("data") or {}

	if delivery_id and _is_duplicate_delivery(delivery_id):
		return {"ok": True, "duplicate": True}

	if delivery_id:
		_mark_delivery_seen(delivery_id)

	frappe.enqueue(
		"freightmas.integrations.tracking.webhook.process_webhook_event",
		queue="short",
		event=event,
		data=data,
		delivery_id=delivery_id,
	)

	return {"ok": True}


def process_webhook_event(event, data, delivery_id=None):
	"""Process a Traqo webhook asynchronously."""
	reference = (data.get("reference_number") or "").strip()
	shipment_id = (data.get("shipment_id") or "").strip()

	if not reference and not shipment_id:
		return

	for doctype, method in (
		("Forwarding Job", "freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.fetch_containers_from_bl"),
		("Clearing Job", "freightmas.clearing_service.doctype.clearing_job.clearing_job.fetch_containers_from_bl"),
	):
		job_filters = {"enable_api_tracking": 1, "docstatus": ["<", 2]}
		if reference:
			job_filters["bl_number"] = reference
		elif shipment_id:
			job_filters["traqo_shipment_id"] = shipment_id

		jobs = frappe.get_all(doctype, filters=job_filters, pluck="name")
		for job_name in jobs:
			try:
				frappe.get_attr(method)(job_name)
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				frappe.log_error(title=f"Traqo webhook refresh failed [{doctype}]: {job_name}")


def _verify_signature(raw_body, header, tolerance_sec=300):
	settings = frappe.get_single("FreightMas Settings")
	secret = settings.get_password("traqo_webhook_secret")
	if not secret or not header:
		return False

	parts = {}
	for piece in header.split(","):
		if "=" in piece:
			key, value = piece.split("=", 1)
			parts[key.strip()] = value.strip()

	timestamp = parts.get("t")
	signature = parts.get("v1")
	if not timestamp or not signature:
		return False

	try:
		ts = int(timestamp)
	except ValueError:
		return False

	if abs(int(time.time()) - ts) > tolerance_sec:
		return False

	expected = hmac.new(
		secret.encode("utf-8"),
		f"{timestamp}.{raw_body}".encode("utf-8"),
		hashlib.sha256,
	).hexdigest()

	return hmac.compare_digest(signature, expected)


def _is_duplicate_delivery(delivery_id):
	return bool(frappe.cache().get_value(f"traqo_webhook:{delivery_id}"))


def _mark_delivery_seen(delivery_id):
	frappe.cache().set_value(f"traqo_webhook:{delivery_id}", 1, expires_in_sec=86400)
