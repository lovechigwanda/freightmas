# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Apply provider-specific extras and Traqo lifecycle helpers."""

import frappe

from freightmas.integrations.tracking.base import get_tracking_provider
from freightmas.integrations.tracking.dispatcher import untrack_shipment


def apply_provider_extras(doc, tracking):
	"""Persist Traqo-specific fields on a job document."""
	extras = tracking.get("provider_extras") or {}
	if not extras:
		return

	if extras.get("traqo_shipment_id"):
		doc.traqo_shipment_id = extras["traqo_shipment_id"]
	if extras.get("tracking_public_url"):
		doc.tracking_public_url = extras["tracking_public_url"]
	if extras.get("predictive_eta"):
		doc.predictive_eta = extras["predictive_eta"]
	if extras.get("is_delayed") is not None:
		doc.is_delayed = 1 if extras.get("is_delayed") else 0
	if extras.get("eta_reliable") is not None:
		doc.eta_reliable = 1 if extras.get("eta_reliable") else 0

	_append_eta_history(doc, extras.get("eta_history") or [])


def _append_eta_history(doc, history_rows):
	if not history_rows or not hasattr(doc, "tracking_timeline"):
		return

	for row in history_rows:
		if not row.get("eta"):
			continue
		event_text = f"ETA updated to {row['eta']}"
		if row.get("previous_eta"):
			event_text = f"ETA changed from {row['previous_eta']} to {row['eta']}"

		already_logged = any(
			(getattr(tl, "source", None) == "API" and getattr(tl, "event", None) == event_text)
			for tl in (doc.get("tracking_timeline") or [])
		)
		if already_logged:
			continue

		doc.append("tracking_timeline", {
			"source": "API",
			"event": event_text,
			"date": row.get("recorded_at") or frappe.utils.now_datetime(),
			"last_verified": frappe.utils.now_datetime(),
			"updated_by": "Administrator",
		})


def append_clearing_eta_history(doc, history_rows):
	"""Append ETA history notes to clearing job tracking table."""
	if not history_rows:
		return

	for row in history_rows:
		if not row.get("eta"):
			continue
		comment = f"ETA updated to {row['eta']}"
		if row.get("previous_eta"):
			comment = f"ETA changed from {row['previous_eta']} to {row['eta']}"

		already_logged = any(
			(getattr(tl, "source", None) == "API" and getattr(tl, "comment", None) == comment)
			for tl in (doc.get("clearing_tracking") or [])
		)
		if already_logged:
			continue

		now = frappe.utils.now_datetime()
		doc.append("clearing_tracking", {
			"source": "API",
			"comment": comment,
			"updated_on": now,
			"last_verified": now,
			"updated_by": "Administrator",
		})


def release_traqo_slot(doc):
	"""Untrack a completed/cancelled job in Traqo to free shipment slots."""
	if get_tracking_provider() != "Traqo":
		return
	if not doc.get("traqo_shipment_id"):
		return

	if untrack_shipment(doc.traqo_shipment_id):
		doc.traqo_shipment_id = ""


def on_forwarding_job_update(doc, method=None):
	if doc.status not in ("Completed", "Cancelled"):
		return
	if doc.get_doc_before_save() and doc.get_doc_before_save().status == doc.status:
		return
	release_traqo_slot(doc)


def on_clearing_job_update(doc, method=None):
	if doc.status not in ("Completed", "Cancelled"):
		return
	if doc.get_doc_before_save() and doc.get_doc_before_save().status == doc.status:
		return
	release_traqo_slot(doc)
