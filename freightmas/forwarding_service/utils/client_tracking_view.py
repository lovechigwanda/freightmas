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

PDF_STATUS_COLORS = {
	"orange": "#dd6b20",
	"green": "#15803d",
	"red": "#b91c1c",
	"gray": "#98a1ac",
}

PDF_PROGRESS_COLORS = {
	"none": "#b91c1c",
	"started": "#b45309",
	"progress": "#4338ca",
	"complete": "#15803d",
}

PHASE_TONE = {
	"planning": "neutral",
	"awaiting_departure": "neutral",
	"in_transit": "blue",
	"at_terminal": "teal",
	"under_port_clearance": "purple",
	"under_border_clearance": "orange",
	"on_road": "amber",
	"at_warehouse": "amber",
	"delivered": "green",
	"closed": "neutral",
	"cancelled": "red",
}

PHASE_TONE_COLORS = {
	"neutral": "#64748b",
	"blue": "#2563eb",
	"teal": "#0d9488",
	"purple": "#7c3aed",
	"orange": "#ea580c",
	"amber": "#d97706",
	"green": "#15803d",
	"red": "#b91c1c",
}

# Client journey display order (operational flow, not internal section build order).
JOURNEY_SECTION_ORDER = (
	"Sea / Air Freight",
	"Port Clearance",
	"Road Transport",
	"Border Clearance",
	"Completion",
)

JOURNEY_STEP_LABELS = {
	"Sea / Air Freight": "Sea / Air",
	"Port Clearance": "Port",
	"Road Transport": "Road",
	"Border Clearance": "Border",
	"Completion": "Delivered",
}

# Rough progress for shipment list rows — aligned with operational phase, not ops checklists.
CLIENT_LIST_PHASE_PROGRESS = {
	"planning": 5,
	"awaiting_departure": 15,
	"in_transit": 35,
	"at_terminal": 50,
	"under_port_clearance": 65,
	"under_border_clearance": 75,
	"on_road": 85,
	"at_warehouse": 90,
	"delivered": 100,
	"closed": 100,
	"cancelled": 0,
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


def client_list_progress(doc_or_row):
	"""Single client-facing progress value for list views."""
	status = getattr(doc_or_row, "status", None) or doc_or_row.get("status")
	if status in ("Delivered", "Completed", "Closed"):
		return 100
	phase = getattr(doc_or_row, "operational_phase", None) or doc_or_row.get("operational_phase")
	return CLIENT_LIST_PHASE_PROGRESS.get(phase, 0)


def _section_is_complete(section):
	if section.get("kind") == "completion":
		return bool(section.get("completed"))
	progress = section.get("progress") or {}
	return progress.get("percent", 0) >= 100


def _phase_summary(section, doc):
	"""One-line client summary for a journey phase."""
	kind = section.get("kind")
	if kind == "completion":
		if section.get("completed_on"):
			return f"Completed · {formatdate(section['completed_on'], 'dd-MMM-yy')}"
		if section.get("completed"):
			return "Completed"
		return "Pending"

	if kind == "sea_air":
		done_stages = [s for s in (section.get("shipment_stages") or []) if s.get("done")]
		if done_stages:
			last = done_stages[-1]
			date_str = formatdate(last["date"], "dd-MMM-yy") if last.get("date") else ""
			return f"{last['label']}{f' · {date_str}' if date_str else ''}"
		return "Awaiting departure"

	if kind == "road":
		progress = section.get("progress") or {}
		if progress.get("percent", 0) >= 100:
			return "Delivered to destination"
		if progress.get("done", 0) > 0:
			return f"{progress['done']} of {progress['total']} steps complete"
		return "Not started"

	if kind in ("clearance_checklist", "clearance_stages"):
		progress = section.get("progress") or {}
		if progress.get("percent", 0) >= 100:
			return "Clearance complete"
		if kind == "clearance_stages":
			current = next((s for s in (section.get("stages") or []) if s.get("is_current")), None)
			if current:
				return f"In progress · {current['name']}"
		return f"{progress.get('done', 0)} of {progress.get('total', 0)} items complete"

	return ""


def _assign_journey_states(phases, is_terminal):
	"""Mark each phase done / current / pending."""
	if is_terminal:
		for phase in phases:
			phase["state"] = "done"
			total = (phase.get("progress") or {}).get("total") or 1
			phase["progress"] = _progress_fraction(total, total)
		return phases

	current_set = False
	for phase in phases:
		if _section_is_complete(phase.get("section") or {}):
			phase["state"] = "done"
		elif not current_set:
			phase["state"] = "current"
			current_set = True
		else:
			phase["state"] = "pending"
	return phases


def _build_journey_phases(sections, doc, status_key):
	"""Ordered client journey phases derived from tracking sections."""
	by_title = {section["title"]: section for section in sections}
	phases = []
	for title in JOURNEY_SECTION_ORDER:
		section = by_title.get(title)
		if not section:
			continue
		phases.append({
			"id": section.get("kind") if section.get("kind") != "completion" else "completion",
			"title": title,
			"short_label": JOURNEY_STEP_LABELS.get(title, title),
			"summary": _phase_summary(section, doc),
			"progress": dict(section.get("progress") or _progress_fraction(0, 0)),
			"section": section,
		})

	is_terminal = status_key == "green"
	return _assign_journey_states(phases, is_terminal)


def _build_journey_steps(journey):
	"""Macro step indicators for the hero progress bar."""
	return [
		{
			"id": phase["id"],
			"label": phase["short_label"],
			"state": phase["state"],
		}
		for phase in journey
	]


def _client_journey_progress(journey, status_key):
	"""Phase-weighted progress — always 100% when the shipment is terminal."""
	if status_key == "green":
		return 100
	if not journey:
		return 0

	weight = len(journey)
	accumulated = 0.0
	for phase in journey:
		state = phase.get("state")
		if state == "done":
			accumulated += 1.0
		elif state == "current":
			pct = (phase.get("progress") or {}).get("percent", 0)
			accumulated += max(pct / 100, 0.05)
	return round(accumulated / weight * 100)


def _client_status_label(doc, status_key):
	if status_key == "green":
		if doc.status == "Delivered":
			return "Delivered"
		if doc.status in ("Completed", "Closed"):
			return "Completed"
		return "Delivered"
	if status_key == "red":
		return "Delayed"
	return get_phase_label(doc.operational_phase) or "In progress"


def _client_status_headline(doc, status_key):
	if doc.current_comment:
		return doc.current_comment
	return dossier_latest_line(doc, status_key)


def _build_client_status(doc, status_key, journey, progress_percent):
	return {
		"key": status_key,
		"label": _client_status_label(doc, status_key),
		"headline": _client_status_headline(doc, status_key),
		"progress_percent": progress_percent,
		"is_terminal": status_key == "green",
		"current_phase_index": next(
			(i for i, phase in enumerate(journey) if phase.get("state") == "current"),
			len(journey) - 1 if journey else 0,
		),
	}


def _build_client_containers(cargo, doc, status_key):
	"""Simplified container rows for the client portal."""
	rows = []
	for row in cargo:
		number = row.get("container_number")
		if not number or number == "–":
			continue

		if status_key == "green" or row.get("is_completed") or row.get("gate_out_date"):
			status = "Delivered"
		elif row.get("api_container_status"):
			status = row["api_container_status"]
		else:
			status = "In Transit"

		last_event = row.get("api_last_event")
		last_event_date = row.get("api_last_event_date")
		if not last_event and row.get("gate_out_date"):
			last_event = "Gated out to consignee"
			last_event_date = row.get("gate_out_date")
		elif not last_event and doc.current_comment:
			last_event = doc.current_comment

		rows.append({
			"container_number": number,
			"container_type": row.get("container_type") or "–",
			"status": status,
			"last_event": last_event or "–",
			"last_event_date": last_event_date,
			"discharge_date": row.get("discharge_date"),
			"gate_out_date": row.get("gate_out_date"),
			"empty_return_date": row.get("empty_return_date"),
			"to_be_returned": row.get("to_be_returned"),
			"is_truck_required": row.get("is_truck_required"),
			"booked_on_date": row.get("booked_on_date"),
			"loaded_on_date": row.get("loaded_on_date"),
			"offloaded_on_date": row.get("offloaded_on_date"),
			"returned_on_date": row.get("returned_on_date"),
			"completed_on_date": row.get("completed_on_date"),
		})
	return rows


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

	completed = doc.status in ("Completed", "Closed", "Delivered") or bool(doc.completed_on)
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

	journey = _build_journey_phases(sections, doc, status_key)
	client_progress = _client_journey_progress(journey, status_key)
	client_status = _build_client_status(doc, status_key, journey, client_progress)
	containers = _build_client_containers(cargo, doc, status_key)
	steps = _build_journey_steps(journey)

	return {
		"banner": {
			"status_key": status_key,
			"status_label": DOSSIER_STATUS_LABELS.get(status_key, "In Progress"),
			"operational_phase": doc.operational_phase,
			"operational_phase_label": get_phase_label(doc.operational_phase),
			"progress_percent": client_progress,
			"latest_update": dossier_latest_line(doc, status_key),
			"key_date_label": key_date_label,
			"key_date": key_date,
		},
		"client_status": client_status,
		"journey": journey,
		"steps": steps,
		"containers": containers,
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


def pdf_progress_class(percent):
	if percent >= 100:
		return "complete"
	if percent >= 50:
		return "progress"
	if percent > 0:
		return "started"
	return "none"


def pdf_progress_color(percent):
	return PDF_PROGRESS_COLORS[pdf_progress_class(percent)]


def pdf_primary_label(doc):
	return doc.customer_reference or doc.bl_number or doc.name


def pdf_route_line(doc):
	origin = doc.port_of_loading or "–"
	dest = doc.destination or doc.port_of_discharge or "–"
	parts = [f"{origin} → {dest}"]
	if doc.direction:
		parts.append(doc.direction)
	if doc.shipment_mode and doc.shipment_type:
		parts.append(f"{doc.shipment_mode} · {doc.shipment_type}")
	return " · ".join(parts)


def pdf_headline(doc, status_key):
	if doc.current_comment:
		return doc.current_comment
	if doc.operational_phase:
		return get_phase_label(doc.operational_phase)
	primary = pdf_primary_label(doc)
	if doc.name and doc.name != primary:
		return doc.name
	return "No tracking update yet"


def pdf_eta_display(doc, is_overdue):
	is_export = doc.direction == "Export"
	date = doc.etd if is_export else doc.eta
	label = "ETD" if is_export else "ETA"
	if not date:
		return {"label": label, "display": "–", "urgency": "normal"}
	return {
		"label": label,
		"display": f"{label} {formatdate(date, 'dd MMM yyyy')}",
		"urgency": "overdue" if is_overdue else "normal",
	}


def pdf_cargo_units(cargo):
	from collections import Counter

	type_counts = Counter(c["container_type"] for c in cargo if c.get("container_type"))
	return " + ".join(f"{n}×{t}" for t, n in type_counts.items())


def _pdf_journey_status_text(phase):
	state = phase.get("state")
	if state == "done":
		return "Done"
	if state == "pending":
		return "Pending"

	progress = phase.get("progress") or {}
	pct = progress.get("percent", 0)
	section = phase.get("section") or {}
	if section.get("kind") == "clearance_stages":
		current = next((s for s in (section.get("stages") or []) if s.get("is_current")), None)
		if current and current.get("missing"):
			count = len(current["missing"])
			doc_word = "documents" if count != 1 else "document"
			return f"Current · {count} {doc_word} outstanding"
	if pct:
		return f"Current · {pct}%"
	return "Current"


def _pdf_fact_strip(doc):
	return [
		{"label": "BL Number", "value": doc.bl_number or "—"},
		{"label": "Customer Ref", "value": doc.customer_reference or "—"},
		{
			"label": "ETD / ATD",
			"value": (
				f"{formatdate(doc.etd, 'dd MMM yyyy') if doc.etd else '—'}"
				f" · {formatdate(doc.atd, 'dd MMM yyyy') if doc.atd else 'Pending'}"
			),
		},
		{
			"label": "ETA / ATA",
			"value": (
				f"{formatdate(doc.eta, 'dd MMM yyyy') if doc.eta else '—'}"
				f" · {formatdate(doc.ata, 'dd MMM yyyy') if doc.ata else 'Pending'}"
			),
		},
		{
			"label": "Cargo",
			"value": " · ".join(
				part for part in [doc.cargo_description, str(doc.cargo_count) if doc.cargo_count else None] if part
			)
			or "—",
		},
		{
			"label": "Discharge",
			"value": formatdate(doc.discharge_date, "dd MMM yyyy") if doc.discharge_date else "—",
		},
	]


def build_pdf_job_context(doc):
	"""Client-portal-shaped context for the Shipment Tracking PDF."""
	today = getdate(nowdate())
	status_key = dossier_status_key(doc, today)
	tracking = build_client_tracking_view(doc)
	client_status = tracking["client_status"]
	banner = tracking["banner"]

	is_overdue = status_key == "red"
	primary_label = pdf_primary_label(doc)
	secondary_label = doc.name if primary_label != doc.name else None
	cargo = build_job_cargo_list(doc)
	cargo_units = pdf_cargo_units(cargo)
	eta = pdf_eta_display(doc, is_overdue)
	progress_percent = client_status["progress_percent"]
	progress_class = pdf_progress_class(progress_percent)
	phase_tone = PHASE_TONE.get(doc.operational_phase, "neutral")

	is_import = doc.direction == "Import"
	sort_date = doc.eta if is_import else doc.etd

	journey_rows = [
		{
			"title": phase["title"],
			"state": phase["state"],
			"summary": phase["summary"] or "—",
			"status_text": _pdf_journey_status_text(phase),
			"progress_percent": (phase.get("progress") or {}).get("percent", 0),
		}
		for phase in tracking["journey"]
	]

	container_rows = [
		{
			"container_number": row["container_number"],
			"container_type": row["container_type"],
			"status": row["status"],
			"last_event": row["last_event"],
			"last_event_date": formatdate(row["last_event_date"], "dd MMM yyyy")
			if row.get("last_event_date")
			else "—",
		}
		for row in tracking["containers"]
	]

	key_date = banner.get("key_date")
	key_date_label = banner.get("key_date_label") or "ETA"
	mode_parts = [doc.shipment_mode, doc.shipment_type]
	cargo_display = " · ".join(
		part
		for part in [
			doc.cargo_description,
			cargo_units if cargo_units and cargo_units != "—" else None,
		]
		if part
	) or "—"

	return {
		"ref": doc.name,
		"bl_number": doc.bl_number or "—",
		"direction": doc.direction or "—",
		"mode": " · ".join(part for part in mode_parts if part) or "—",
		"cargo_display": cargo_display,
		"dates": {
			"etd": doc.etd,
			"atd": doc.atd,
			"eta": doc.eta,
			"ata": doc.ata,
			"discharge_date": doc.discharge_date,
			"completed_on": doc.completed_on,
		},
		"status_key": status_key,
		"status_color": PDF_STATUS_COLORS.get(status_key, PDF_STATUS_COLORS["gray"]),
		"status_label": DOSSIER_STATUS_LABELS.get(status_key, "In Progress"),
		"is_overdue": is_overdue,
		"sort_date": sort_date,
		"progress_percent": progress_percent,
		"progress_class": progress_class,
		"progress_color": pdf_progress_color(progress_percent),
		"glance": {
			"primary_label": primary_label,
			"secondary_label": secondary_label,
			"route": pdf_route_line(doc).split(" · ")[0],
			"phase_label": banner.get("operational_phase_label") or get_phase_label(doc.operational_phase) or "—",
			"phase_tone": phase_tone,
			"phase_color": PHASE_TONE_COLORS.get(phase_tone, PHASE_TONE_COLORS["neutral"]),
			"eta_display": eta["display"],
			"eta_urgency": eta["urgency"],
			"headline": pdf_headline(doc, status_key),
			"cargo_units": cargo_units,
			"progress_percent": progress_percent,
			"progress_class": progress_class,
			"progress_color": pdf_progress_color(progress_percent),
		},
		"hero": {
			"status_label": client_status["label"],
			"headline": client_status["headline"],
			"route_line": pdf_route_line(doc),
			"key_date_label": key_date_label,
			"key_date_display": formatdate(key_date, "dd MMM yyyy") if key_date else "—",
			"key_date_urgency": "overdue" if is_overdue else "normal",
			"is_delayed": is_overdue,
			"progress_percent": progress_percent,
			"progress_class": progress_class,
			"progress_color": pdf_progress_color(progress_percent),
			"steps": tracking["steps"],
		},
		"facts": _pdf_fact_strip(doc),
		"journey": journey_rows,
		"containers": container_rows,
	}
