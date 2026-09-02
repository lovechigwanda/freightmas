# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Phase-driven tracking headline orchestration for Forwarding Jobs."""

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import formatdate, getdate, now_datetime

from freightmas.forwarding_service.utils.operational_phase import (
	_containerised_parcels,
	_milestones_started,
	_truck_parcels,
	_trucking_in_progress,
	derive_operational_phase,
	get_phase_label,
)

SERVICE_SEA_AIR = "Sea / Air Freight"
SERVICE_PORT_CLEARANCE = "Port Clearance"
SERVICE_ROAD = "Road Transport"
SERVICE_BORDER = "Border Clearance"
SERVICE_WAREHOUSE = "Warehouse"
SERVICE_GENERAL = "General"

SERVICE_COMMENT_FIELDS = (
	("port_clearance_tracking_comment", SERVICE_PORT_CLEARANCE),
	("road_transport_tracking_comment", SERVICE_ROAD),
	("border_clearance_tracking_comment", SERVICE_BORDER),
	("warehouse_tracking_comment", SERVICE_WAREHOUSE),
)

ROAD_MILESTONE_COUNT_STAGES = (
	("booked", lambda row: getattr(row, "is_booked", 0)),
	("loaded", lambda row: getattr(row, "is_loaded", 0)),
	("at border", lambda row: getattr(row, "border_arrived_on", None)),
	("at border 2", lambda row: getattr(row, "border_2_arrived_on", None)),
	("at offloading point", lambda row: getattr(row, "offloading_arrived_on", None)),
	("offloaded", lambda row: getattr(row, "is_offloaded", 0)),
	("returned", lambda row: getattr(row, "is_returned", 0)),
	("completed", lambda row: getattr(row, "is_completed", 0)),
)

ROAD_SIGNIFICANT_MILESTONES = frozenset({
	"loaded",
	"border1_arrived",
	"border1_left",
	"border2_arrived",
	"border2_left",
	"offload_arrived",
	"offloaded",
})


def _append_timeline_row(doc, row: dict) -> None:
	if isinstance(doc, Document):
		doc.append("tracking_timeline", row)
	else:
		doc.setdefault("tracking_timeline", []).append(frappe._dict(row))


def api_owns_job_narrative(doc) -> bool:
	"""True while sea/air API may append job timeline rows."""
	phase = derive_operational_phase(doc)["phase"]
	if phase in ("planning", "awaiting_departure", "in_transit"):
		return True
	if phase == "at_terminal":
		if _milestones_started(doc, "port_clearance_milestones"):
			return False
		if (doc.get("port_clearance_tracking_comment") or "").strip():
			return False
		if _trucking_in_progress(doc):
			return False
		return True
	return False


def resolve_client_headline(doc) -> str:
	"""Phase-driven headline used everywhere forwarding tracking is shown."""
	phase = derive_operational_phase(doc)["phase"]

	if phase == "under_port_clearance":
		return (doc.get("port_clearance_tracking_comment") or "").strip() or get_phase_label(phase)
	if phase == "under_border_clearance":
		return (doc.get("border_clearance_tracking_comment") or "").strip() or get_phase_label(phase)
	if phase == "at_warehouse":
		return (doc.get("warehouse_tracking_comment") or "").strip() or get_phase_label(phase)
	if phase == "on_road":
		return build_road_client_headline(doc) or get_phase_label(phase)
	if phase in ("planning", "awaiting_departure", "in_transit"):
		return _sea_air_headline(doc) or get_phase_label(phase)
	if phase == "at_terminal":
		return _terminal_headline(doc) or get_phase_label(phase)
	if phase == "delivered":
		return "Delivered"
	if phase == "closed":
		return get_phase_label(phase)
	if phase == "cancelled":
		return get_phase_label(phase)
	return (doc.get("current_comment") or "").strip() or get_phase_label(phase) or ""


def _parcel_highest_road_stage(row) -> str | None:
	"""Return the highest road milestone reached for one truck-required parcel."""
	latest = None
	for label, is_done in ROAD_MILESTONE_COUNT_STAGES:
		if is_done(row):
			latest = label
	return latest


def road_milestone_count_summary(doc) -> str | None:
	"""Auto-generated milestone counts across truck-required parcels."""
	parcels = _truck_parcels(doc)
	if not parcels:
		return None

	buckets: dict[str, int] = {}
	for row in parcels:
		stage = _parcel_highest_road_stage(row)
		if stage:
			buckets[stage] = buckets.get(stage, 0) + 1

	if not buckets:
		return None

	single_parcel = len(parcels) == 1
	parts = []
	for label, _is_done in ROAD_MILESTONE_COUNT_STAGES:
		count = buckets.get(label, 0)
		if not count:
			continue
		if single_parcel:
			parts.append(label.title())
		else:
			parts.append(f"{count} {label}")

	return ", ".join(parts) if parts else None


def build_road_client_headline(doc) -> str | None:
	"""Combine auto load counts with the job-level road service comment."""
	counts = road_milestone_count_summary(doc)
	comment = (doc.get("road_transport_tracking_comment") or "").strip()
	if counts and comment:
		return f"{counts} · {comment}"
	return counts or comment or None


def sync_current_comment(doc) -> None:
	"""Set current_comment and last-updated fields from resolve_client_headline."""
	headline = resolve_client_headline(doc)
	if not headline:
		return

	previous = (doc.get("current_comment") or "").strip()
	doc.current_comment = headline
	if headline != previous:
		doc.last_updated_on = now_datetime()
		user = frappe.session.user if frappe.session.user and frappe.session.user != "Guest" else None
		if user:
			doc.last_updated_by = user


def append_service_comment_to_timeline(doc, comment: str, service: str) -> None:
	"""Log a service tracking comment change to the job timeline."""
	comment = (comment or "").strip()
	if not comment:
		return

	last_row = None
	for row in reversed(doc.get("tracking_timeline") or []):
		if getattr(row, "service", None) == service and row.source == "Manual":
			last_row = row
			break

	if last_row and (last_row.event or "").strip() == comment:
		last_row.last_verified = now_datetime()
		return

	_append_timeline_row(doc, {
		"source": "Manual",
		"service": service,
		"event": comment,
		"date": now_datetime(),
		"last_verified": now_datetime(),
		"updated_by": frappe.session.user or "Administrator",
	})


def append_road_timeline_event(doc, comment: str | None, milestone: str | None = None) -> None:
	"""Append a road transport event to the job timeline."""
	event = (comment or "").strip()
	if not event and milestone:
		event = _default_road_milestone_text(milestone)
	if not event:
		return

	last_row = None
	for row in reversed(doc.get("tracking_timeline") or []):
		if getattr(row, "service", None) == SERVICE_ROAD and row.source == "Manual":
			last_row = row
			break

	if last_row and (last_row.event or "").strip() == event:
		last_row.last_verified = now_datetime()
		return

	_append_timeline_row(doc, {
		"source": "Manual",
		"service": SERVICE_ROAD,
		"event": event,
		"date": now_datetime(),
		"last_verified": now_datetime(),
		"updated_by": frappe.session.user or "Administrator",
	})


def sync_service_comment_timeline_changes(doc, previous: dict | None = None) -> None:
	"""Append timeline rows when port/border/warehouse tracking comments change."""
	for fieldname, service in SERVICE_COMMENT_FIELDS:
		current = (doc.get(fieldname) or "").strip()
		old = (previous.get(fieldname) or "").strip() if previous else ""
		if current and current != old:
			append_service_comment_to_timeline(doc, current, service)


def _sea_air_headline(doc) -> str | None:
	if doc.get("api_last_event"):
		parts = [doc.api_last_event]
		if doc.get("api_last_event_date"):
			try:
				parts.append(formatdate(getdate(doc.api_last_event_date), "dd-MMM-yy"))
			except Exception:
				parts.append(str(doc.api_last_event_date))
		return ": ".join(parts) if len(parts) > 1 else parts[0]

	for row in reversed(doc.get("tracking_timeline") or []):
		if row.source == "API" and (row.event or "").strip():
			return row.event.strip()
	return None


def _terminal_headline(doc) -> str | None:
	latest_event = None
	latest_date = None
	for row in _containerised_parcels(doc):
		event = (getattr(row, "api_last_event", None) or "").strip()
		event_date = getattr(row, "api_last_event_date", None)
		if event and event_date and (not latest_date or event_date > latest_date):
			latest_event = event
			latest_date = event_date
	if latest_event:
		try:
			return f"{latest_event}: {formatdate(getdate(latest_date), 'dd-MMM-yy')}"
		except Exception:
			return latest_event
	return _sea_air_headline(doc)


def _default_road_milestone_text(milestone: str) -> str:
	labels = {
		"loaded": "Container loaded",
		"border1_arrived": "Arrived at border",
		"border1_left": "Departed border",
		"border2_arrived": "Arrived at border 2",
		"border2_left": "Departed border 2",
		"offload_arrived": "Arrived at offloading point",
		"offloaded": "Container offloaded",
		"booked": "Transport booked",
		"returned": "Empty container returned",
		"completed": "Delivery completed",
	}
	label = labels.get(milestone, milestone.replace("_", " ").title())
	return f"Road Transport - {label}: {formatdate(now_datetime(), 'dd-MMM-yy')}"
