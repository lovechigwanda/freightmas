# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Derive the operational progress phase for Forwarding Jobs.

Single source of truth for bucket assignment used by the DocType (persisted
fields), Shipment Dashboard, Client Portal, reports, and list views.
"""

from __future__ import annotations

import json

import frappe
from frappe.utils import cint

OPERATIONAL_PHASES = (
	"planning",
	"awaiting_departure",
	"in_transit",
	"at_terminal",
	"under_port_clearance",
	"under_border_clearance",
	"on_road",
	"at_warehouse",
	"delivered",
	"closed",
	"cancelled",
)

OPERATIONAL_PHASE_LABELS = {
	"planning": "Planning",
	"awaiting_departure": "Awaiting Departure",
	"in_transit": "In Transit",
	"at_terminal": "At Terminal",
	"under_port_clearance": "Under Port Clearance",
	"under_border_clearance": "Under Border Clearance",
	"on_road": "On Road",
	"at_warehouse": "At Warehouse",
	"delivered": "Delivered",
	"closed": "Closed",
	"cancelled": "Cancelled",
}

OPERATIONAL_PHASE_OPTIONS = "\n".join(OPERATIONAL_PHASES)

MILESTONE_TABLE_FIELDS = (
	"road_freight_milestones",
	"port_clearance_milestones",
	"border_clearance_milestones",
	"warehouse_milestones",
)

# Dashboard overview pipeline — display buckets (subset of operational phases).
# `label` is the short card text; `title` is the full name for tooltips.
OVERVIEW_PIPELINE_BUCKETS = (
	{"key": "at_origin", "label": "At Origin", "title": "At Origin", "phases": ("planning", "awaiting_departure")},
	{"key": "in_transit", "label": "In Water / Air", "title": "In Water / Air", "phases": ("in_transit",)},
	{"key": "at_terminal", "label": "At POD", "title": "At Port of Discharge", "phases": ("at_terminal",)},
	{"key": "under_port_clearance", "label": "Port Clearance", "title": "Under Port Clearance", "phases": ("under_port_clearance",)},
	{"key": "under_border_clearance", "label": "Border Clearance", "title": "Under Border Clearance", "phases": ("under_border_clearance",)},
	{"key": "on_road", "label": "On Road", "title": "On Road to Destination", "phases": ("on_road",)},
	{"key": "delivered", "label": "Delivered", "title": "Delivered", "phases": ("delivered",)},
)

_OVERVIEW_BUCKET_BY_KEY = {bucket["key"]: bucket for bucket in OVERVIEW_PIPELINE_BUCKETS}


def get_overview_bucket(bucket_key):
	"""Return overview pipeline bucket config or None."""
	return _OVERVIEW_BUCKET_BY_KEY.get(bucket_key)


def get_overview_bucket_phases(bucket_key):
	"""Operational phase values included in an overview pipeline bucket."""
	bucket = get_overview_bucket(bucket_key)
	return list(bucket["phases"]) if bucket else []


def resolve_operational_phase_filter(operational_phase=None, operational_phases=None, overview_bucket=None):
	"""Return a frappe filter value for operational_phase, or None."""
	bucket_phases = get_overview_bucket_phases(overview_bucket) if overview_bucket else []
	if bucket_phases:
		return ["in", bucket_phases] if len(bucket_phases) > 1 else bucket_phases[0]

	phases = []
	if operational_phases:
		if isinstance(operational_phases, str):
			raw = operational_phases.strip()
			if raw.startswith("["):
				try:
					parsed = json.loads(raw)
					phases = [phase for phase in parsed if phase]
				except (json.JSONDecodeError, TypeError):
					phases = [phase.strip() for phase in raw.split(",") if phase.strip()]
			else:
				phases = [phase.strip() for phase in raw.split(",") if phase.strip()]
		elif isinstance(operational_phases, (list, tuple)):
			phases = [phase for phase in operational_phases if phase]

	if not phases and operational_phase:
		phases = [operational_phase]

	if not phases:
		return None
	if len(phases) == 1:
		return phases[0]
	return ["in", phases]


def build_overview_phase_pipeline(customers=None):
	"""Counts per overview pipeline bucket from persisted operational_phase."""
	visible_phases = {phase for bucket in OVERVIEW_PIPELINE_BUCKETS for phase in bucket["phases"]}
	if not visible_phases:
		return []

	params = {"phases": tuple(visible_phases)}
	customer_clause = ""
	if customers:
		customer_clause = " AND customer IN %(customers)s"
		params["customers"] = tuple(customers)

	rows = frappe.db.sql(
		f"""
		SELECT operational_phase, COUNT(*) AS count
		FROM `tabForwarding Job`
		WHERE docstatus < 2 AND operational_phase IN %(phases)s{customer_clause}
		GROUP BY operational_phase
		""",
		params,
		as_dict=True,
	)
	counts_by_phase = {row.operational_phase: row.count for row in rows}

	pipeline = []
	for bucket in OVERVIEW_PIPELINE_BUCKETS:
		count = sum(counts_by_phase.get(phase, 0) for phase in bucket["phases"])
		pipeline.append({
			"key": bucket["key"],
			"label": bucket["label"],
			"title": bucket.get("title") or bucket["label"],
			"count": count,
			"phases": list(bucket["phases"]),
		})
	return pipeline


def get_phase_label(phase):
	return OPERATIONAL_PHASE_LABELS.get(phase, phase or "")


def set_operational_phase(doc):
	"""Persist derived phase fields on a Forwarding Job document."""
	result = derive_operational_phase(doc)
	doc.operational_phase = result["phase"]
	doc.operational_substage = result.get("substage") or ""


def derive_operational_phase(doc):
	"""Return {phase, substage, label} for a loaded Forwarding Job."""
	phase = _resolve_phase(doc)
	substage = _resolve_substage(doc, phase)
	return {
		"phase": phase,
		"substage": substage,
		"label": get_phase_label(phase),
	}


def operational_phase_map(job_names):
	"""Bulk {job_name: {phase, substage, label}} for list endpoints."""
	if not job_names:
		return {}

	result = {}
	for name in job_names:
		doc = frappe.get_doc("Forwarding Job", name)
		result[name] = derive_operational_phase(doc)
	return result


def _resolve_phase(doc):
	status = doc.status or "Draft"

	if status == "Cancelled":
		return "cancelled"
	if status in ("Completed", "Closed"):
		return "closed"
	if _is_operationally_delivered(doc):
		return "delivered"
	if _warehouse_in_progress(doc):
		return "at_warehouse"
	if _trucking_in_progress(doc):
		return "on_road"
	if _port_clearance_in_progress(doc):
		return "under_port_clearance"
	if _border_clearance_in_progress(doc):
		return "under_border_clearance"
	if _at_terminal(doc):
		return "at_terminal"
	if _in_transit(doc):
		return "in_transit"
	if _awaiting_departure(doc):
		return "awaiting_departure"
	return "planning"


def _resolve_substage(doc, phase):
	if phase == "under_port_clearance":
		return _current_substage(doc.get("port_clearance_milestones") or [])
	if phase == "under_border_clearance":
		return _current_substage(doc.get("border_clearance_milestones") or [])
	return ""


def _current_substage(rows):
	if not rows:
		return ""

	buckets = {}
	for row in rows:
		stage = getattr(row, "stage", None) or "Other"
		seq = cint(getattr(row, "stage_sequence", 0))
		bucket = buckets.setdefault(stage, {"done": 0, "total": 0, "seq": seq})
		bucket["total"] += 1
		bucket["seq"] = min(bucket["seq"], seq)
		if getattr(row, "is_completed", 0):
			bucket["done"] += 1

	ordered = sorted(
		buckets.items(),
		key=lambda item: (1, 0) if item[0] == "Other" else (0, item[1]["seq"]),
	)
	for stage, bucket in ordered:
		if bucket["done"] < bucket["total"]:
			return "" if stage == "Other" else stage
	return ""


def _containerised_parcels(doc):
	return [
		row for row in (doc.get("cargo_parcel_details") or [])
		if getattr(row, "cargo_type", None) == "Containerised"
	]


def _truck_parcels(doc):
	return [
		row for row in (doc.get("cargo_parcel_details") or [])
		if getattr(row, "is_truck_required", 0)
	]


def _milestones_complete(doc, fieldname):
	rows = doc.get(fieldname) or []
	if not rows:
		return True
	return all(getattr(row, "is_completed", 0) for row in rows)


def _milestones_started(doc, fieldname):
	rows = doc.get(fieldname) or []
	return any(getattr(row, "is_completed", 0) for row in rows)


def _is_operationally_delivered(doc):
	if doc.status == "Delivered":
		return True

	if doc.requires_port_clearance and not _milestones_complete(doc, "port_clearance_milestones"):
		return False
	if doc.requires_border_clearance and not _milestones_complete(doc, "border_clearance_milestones"):
		return False
	if doc.requires_warehousing and not _milestones_complete(doc, "warehouse_milestones"):
		return False

	if doc.is_trucking_required:
		parcels = _truck_parcels(doc)
		if parcels and all(getattr(row, "is_completed", 0) for row in parcels):
			return True

	if doc.shipment_mode == "Road":
		rows = doc.get("road_freight_milestones") or []
		if rows and all(getattr(row, "is_completed", 0) for row in rows):
			return True

	if not doc.is_trucking_required and not doc.requires_warehousing:
		if doc.requires_sea_air_freight and doc.ata:
			containers = _containerised_parcels(doc)
			if containers:
				for row in containers:
					if not row.gate_out_date:
						return False
					if getattr(row, "to_be_returned", 0) and not row.empty_return_date:
						return False
				return True
			return not doc.requires_port_clearance and not doc.requires_border_clearance

	return False


def _warehouse_in_progress(doc):
	if not doc.requires_warehousing:
		return False
	if _is_operationally_delivered(doc):
		return False
	rows = doc.get("warehouse_milestones") or []
	return bool(rows) and not _milestones_complete(doc, "warehouse_milestones")


def _trucking_in_progress(doc):
	if not doc.is_trucking_required:
		return False
	for row in _truck_parcels(doc):
		if (getattr(row, "is_loaded", 0) or getattr(row, "is_offloaded", 0)) and not getattr(row, "is_completed", 0):
			return True
	return False


def _port_clearance_in_progress(doc):
	if not doc.requires_port_clearance:
		return False
	if _milestones_complete(doc, "port_clearance_milestones"):
		return False

	started = _milestones_started(doc, "port_clearance_milestones")
	if started or doc.ata:
		return True
	if doc.direction == "Export" and doc.status != "Draft":
		return True
	return False


def _border_clearance_in_progress(doc):
	if not doc.requires_border_clearance:
		return False
	if _milestones_complete(doc, "border_clearance_milestones"):
		return False
	if doc.requires_port_clearance and not _milestones_complete(doc, "port_clearance_milestones"):
		return False

	if _milestones_started(doc, "border_clearance_milestones"):
		return True
	if doc.requires_port_clearance and _milestones_complete(doc, "port_clearance_milestones"):
		return True
	if _trucking_in_progress(doc):
		return True
	if doc.direction == "Export" and not doc.atd:
		return True
	return False


def _at_terminal(doc):
	if not (doc.requires_sea_air_freight or _containerised_parcels(doc)):
		return False

	containers = _containerised_parcels(doc)
	if doc.direction in ("Import", "Transit"):
		if doc.ata:
			return any(not row.gate_out_date for row in containers) if containers else True
		if doc.discharge_date:
			return any(not row.gate_out_date for row in containers) if containers else True
	return False


def _in_transit(doc):
	if doc.requires_sea_air_freight and doc.atd and not doc.ata:
		return True

	if doc.shipment_mode == "Road":
		rows = doc.get("road_freight_milestones") or []
		if rows:
			started = _milestones_started(doc, "road_freight_milestones")
			complete = _milestones_complete(doc, "road_freight_milestones")
			if started and not complete and not _trucking_in_progress(doc):
				return True
	return False


def _awaiting_departure(doc):
	if doc.status == "Draft":
		return False
	if doc.requires_sea_air_freight and not doc.atd:
		return True
	if doc.shipment_mode == "Road":
		rows = doc.get("road_freight_milestones") or []
		return not _milestones_started(doc, "road_freight_milestones")
	return False
