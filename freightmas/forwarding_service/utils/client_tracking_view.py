# Client-facing tracking view assembly for Forwarding Jobs.
#
# Shared by the Client Portal, PDF Shipment Tracking dossier, and the
# Command Centre job detail drawer so milestone/cargo/status presentation
# stays in sync.

from __future__ import annotations

import frappe
from frappe.utils import formatdate, getdate, nowdate

from freightmas.forwarding_service.utils.operational_phase import get_phase_label

DOSSIER_STATUS_LABELS = {
	"orange": "In Progress",
	"green": "Completed",
	"red": "Delayed",
	"gray": "In Progress",
}


def milestone_stage_rollup(milestones):
	"""Roll milestones into named stages for summarized client views."""
	buckets = {}
	order = {}
	for m in milestones:
		key = m.get("stage") or None
		seq = m.get("stage_sequence") or 0
		bucket = buckets.setdefault(key, {"done": 0, "total": 0, "missing": []})
		bucket["total"] += 1
		if m.get("is_completed"):
			bucket["done"] += 1
		else:
			bucket["missing"].append(m.get("label"))
		order[key] = min(order[key], seq) if key in order else seq

	ordered = sorted(
		buckets.items(),
		key=lambda item: (1, 0) if item[0] is None else (0, order.get(item[0], 0)),
	)

	stages = []
	current_taken = False
	for key, bucket in ordered:
		pct = round(bucket["done"] / bucket["total"] * 100) if bucket["total"] else 0
		is_current = (not current_taken) and bucket["done"] < bucket["total"]
		if is_current:
			current_taken = True
		stages.append({
			"name": key or "Other",
			"done": bucket["done"],
			"total": bucket["total"],
			"pct": pct,
			"is_current": is_current,
			"missing": bucket["missing"],
		})
	return stages


def has_milestone_stages(milestones):
	return any(m.get("stage") for m in milestones)


def build_job_milestone_stages(doc):
	"""Milestone groups for services required on this job."""
	section_labels = {
		"road_freight_milestones": "Road Freight",
		"port_clearance_milestones": "Port Clearance",
		"border_clearance_milestones": "Border Clearance",
		"warehouse_milestones": "Warehouse",
	}
	requires_map = {
		"road_freight_milestones": True,
		"port_clearance_milestones": doc.requires_port_clearance,
		"border_clearance_milestones": doc.requires_border_clearance,
		"warehouse_milestones": doc.requires_warehousing,
	}
	stages = []
	for fieldname, label in section_labels.items():
		if not requires_map.get(fieldname):
			continue
		rows = doc.get(fieldname) or []
		if not rows:
			continue
		milestones = [
			{
				"label": r.milestone_label,
				"is_completed": bool(r.is_completed),
				"completed_on": r.completed_on,
				"remarks": getattr(r, "remarks", None),
				"stage": r.get("stage"),
				"stage_sequence": r.get("stage_sequence") or 0,
			}
			for r in rows
		]
		stages.append({
			"group": label,
			"milestones": milestones,
			"has_stages": has_milestone_stages(milestones),
			"stages": milestone_stage_rollup(milestones),
		})
	return stages


def build_job_cargo_list(doc):
	"""Cargo/container rows shaped for client tracking views."""
	return [
		{
			"name": r.name,
			"container_number": r.container_number or r.cargo_item_description,
			"container_type": r.container_type,
			"cargo_type": r.cargo_type,
			"to_be_returned": bool(r.to_be_returned),
			"is_truck_required": bool(r.is_truck_required),
			"is_booked": bool(r.is_booked),
			"is_loaded": bool(r.is_loaded),
			"is_offloaded": bool(r.is_offloaded),
			"is_returned": bool(r.is_returned),
			"is_completed": bool(r.is_completed),
			"booked_on_date": r.booked_on_date,
			"loaded_on_date": r.loaded_on_date,
			"offloaded_on_date": r.offloaded_on_date,
			"returned_on_date": r.returned_on_date,
			"completed_on_date": r.completed_on_date,
			"discharge_date": r.discharge_date,
			"gate_out_date": r.gate_out_date,
			"empty_return_date": r.empty_return_date,
			"api_container_status": r.api_container_status,
			"api_last_event": r.api_last_event,
			"api_last_event_date": r.api_last_event_date,
		}
		for r in (doc.cargo_parcel_details or [])
	]


def resolve_client_milestone_report_mode(customer=None):
	if customer:
		override = frappe.db.get_value(
			"Customer", customer, "custom_client_report_milestone_detail"
		)
		if override and override != "Use Default":
			return override
	return (
		frappe.db.get_single_value("FreightMas Settings", "client_report_milestone_detail")
		or "Full Milestones"
	)


def dossier_status_key(doc, today=None):
	today = today or getdate(nowdate())
	if doc.status in ("Completed", "Closed", "Delivered"):
		return "green"
	is_overdue = (
		(doc.direction == "Import" and doc.eta and getdate(doc.eta) < today and not doc.ata)
		or (doc.direction == "Export" and doc.etd and getdate(doc.etd) < today and not doc.atd)
	)
	return "red" if is_overdue else "orange"


def dossier_latest_line(doc, status_key):
	if doc.current_comment:
		return doc.current_comment
	if status_key == "green":
		return "Delivered · Job closed" if doc.status in ("Completed", "Closed") else "Delivered"
	eta = formatdate(doc.eta, "dd-MMM-yy") if doc.eta else None
	if status_key == "red":
		return f"Delayed · Revised ETA {eta}" if eta else "Delayed"
	return f"In transit · ETA {eta}" if eta else "In progress"


def _progress_fraction(done, total):
	pct = round(done / total * 100) if total else 0
	return {"done": done, "total": total, "percent": pct}


def _build_sea_air_shipment_stages(doc):
	is_import = doc.direction == "Import"
	return [
		{
			"label": "Departed Origin (ATD)" if is_import else "Estimated Departure",
			"date": doc.atd or doc.etd,
			"done": bool(doc.atd),
		},
		{
			"label": "Arrived (ATA)" if is_import else "Departed (ATD)",
			"date": doc.ata if is_import else (doc.atd or doc.etd),
			"done": bool(doc.ata) if is_import else bool(doc.atd),
		},
		{
			"label": "Discharged",
			"date": doc.discharge_date,
			"done": bool(doc.discharge_date),
		},
	]


def _sea_air_progress(shipment_stages, containerised_cargo):
	completed = sum(1 for stage in shipment_stages if stage["done"])
	total = len(shipment_stages)
	for row in containerised_cargo:
		checks = [row.get("discharge_date"), row.get("gate_out_date")]
		if row.get("to_be_returned"):
			checks.append(row.get("empty_return_date"))
		total += len(checks)
		completed += sum(1 for value in checks if value)
	return _progress_fraction(completed, total)


def _road_progress(truck_cargo):
	completed = total = 0
	for row in truck_cargo:
		is_returnable = row.get("cargo_type") == "Containerised" and row.get("to_be_returned")
		checks = [
			row.get("is_booked"),
			row.get("is_loaded"),
			row.get("is_offloaded"),
			row.get("is_completed"),
		]
		if is_returnable:
			checks.append(row.get("is_returned") or row.get("empty_return_date"))
		total += len(checks)
		completed += sum(1 for value in checks if value)
	return _progress_fraction(completed, total)


def _build_clearance_section(group, title, use_stage_summary):
	if not group:
		return None
	milestones = group.get("milestones") or []
	done = sum(1 for m in milestones if m.get("is_completed"))
	progress = _progress_fraction(done, len(milestones) or 0)
	if group.get("has_stages"):
		return {
			"kind": "clearance_stages",
			"title": title,
			"progress": progress,
			"stages": group.get("stages") or [],
		}
	return {
		"kind": "clearance_checklist",
		"title": title,
		"progress": progress,
		"entries": [
			{
				"label": m["label"],
				"is_completed": bool(m.get("is_completed")),
				"completed_on": m.get("completed_on"),
			}
			for m in milestones
		],
	}


def build_client_tracking_view(doc, milestone_report_mode=None, milestone_percent=None):
	"""Assemble dossier-style tracking payload for the Client Portal."""
	today = getdate(nowdate())
	cargo = build_job_cargo_list(doc)
	milestone_groups = build_job_milestone_stages(doc)
	groups_by_name = {group["group"]: group for group in milestone_groups}
	status_key = dossier_status_key(doc, today)
	use_stage_summary = (milestone_report_mode or resolve_client_milestone_report_mode(doc.customer)) == "Stage Summary"

	shipment_stages = _build_sea_air_shipment_stages(doc)
	containerised = [row for row in cargo if row.get("cargo_type") == "Containerised"]
	sea_progress = _sea_air_progress(shipment_stages, containerised)

	sea_section = {
		"kind": "sea_air",
		"title": "Sea / Air Freight",
		"progress": sea_progress,
		"shipment_stages": shipment_stages,
		"containers": [
			{
				"container_number": row.get("container_number") or "–",
				"container_type": row.get("container_type") or "–",
				"discharge_date": row.get("discharge_date"),
				"gate_out_date": row.get("gate_out_date"),
				"empty_return_date": row.get("empty_return_date"),
				"to_be_returned": row.get("to_be_returned"),
				"status": row.get("api_container_status")
					or ("Delivered" if row.get("is_completed") else "In Transit"),
			}
			for row in containerised
		],
	}

	sections = [sea_section]

	truck_cargo = [row for row in cargo if row.get("is_truck_required")]
	if truck_cargo:
		sections.append({
			"kind": "road",
			"title": "Road Transport",
			"progress": _road_progress(truck_cargo),
			"containers": [
				{
					"container_number": row.get("container_number") or "–",
					"container_type": row.get("container_type") or "–",
					"cargo_type": row.get("cargo_type"),
					"to_be_returned": row.get("to_be_returned"),
					"is_booked": row.get("is_booked"),
					"is_loaded": row.get("is_loaded"),
					"is_offloaded": row.get("is_offloaded"),
					"is_returned": row.get("is_returned"),
					"is_completed": row.get("is_completed"),
					"booked_on_date": row.get("booked_on_date"),
					"loaded_on_date": row.get("loaded_on_date"),
					"offloaded_on_date": row.get("offloaded_on_date"),
					"returned_on_date": row.get("returned_on_date"),
					"completed_on_date": row.get("completed_on_date"),
					"empty_return_date": row.get("empty_return_date"),
				}
				for row in truck_cargo
			],
		})

	for title in ("Port Clearance", "Border Clearance"):
		section = _build_clearance_section(
			groups_by_name.get(title),
			title,
			use_stage_summary,
		)
		if section:
			sections.append(section)

	completed = doc.status in ("Completed", "Closed") or bool(doc.completed_on)
	sections.append({
		"kind": "completion",
		"title": "Completion",
		"progress": _progress_fraction(1 if completed else 0, 1),
		"completed": completed,
		"completed_on": doc.completed_on,
	})

	if milestone_percent is None:
		milestone_percent = 0

	is_import = doc.direction == "Import"
	key_date = doc.eta if is_import else doc.etd
	key_date_label = "ETA" if is_import else "ETD"

	return {
		"banner": {
			"status_key": status_key,
			"status_label": DOSSIER_STATUS_LABELS.get(status_key, "In Progress"),
			"operational_phase": doc.operational_phase,
			"operational_phase_label": get_phase_label(doc.operational_phase),
			"progress_percent": milestone_percent,
			"latest_update": dossier_latest_line(doc, status_key),
			"key_date_label": key_date_label,
			"key_date": key_date,
		},
		"sections": sections,
		"live_updates": [
			{
				"event": row.event,
				"date": row.date,
				"source": row.source,
			}
			for row in sorted(doc.get("tracking_timeline") or [], key=lambda r: r.idx or 0, reverse=True)
		][:10],
	}
