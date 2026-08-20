# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Overall milestone progress for Forwarding Jobs.

Mirrors the Desk form rollup in forwarding_job.js (render_milestone_summary):
Job Milestone Progress child rows, plus road-transport and sea/air parcel checks.
"""

from __future__ import annotations

import frappe

MILESTONE_TABLE_FIELDS = (
	"road_freight_milestones",
	"port_clearance_milestones",
	"border_clearance_milestones",
	"warehouse_milestones",
)


def road_transport_progress_counts(parcels):
	"""Return (total_checks, done_checks) for truck-required cargo rows."""
	total = 0
	done = 0
	for row in parcels or []:
		if not row.get("is_truck_required"):
			continue
		is_returnable = row.get("cargo_type") == "Containerised" and row.get("to_be_returned")
		checks = [
			bool(row.get("is_booked")),
			bool(row.get("is_loaded")),
			bool(row.get("is_offloaded")),
			bool(row.get("is_completed")),
		]
		if is_returnable:
			checks.append(bool(row.get("is_returned") or row.get("empty_return_date")))
		total += len(checks)
		done += sum(checks)
	return total, done


def sea_air_progress_counts(job, parcels):
	"""Return (total_checks, done_checks) for sea/air shipment + container dates."""
	total = 2
	done = int(bool(job.get("atd"))) + int(bool(job.get("ata")))

	for row in parcels or []:
		if row.get("cargo_type") != "Containerised":
			continue
		checks = [bool(row.get("discharge_date")), bool(row.get("gate_out_date"))]
		if row.get("to_be_returned"):
			checks.append(bool(row.get("empty_return_date")))
		total += len(checks)
		done += sum(checks)

	return total, done


def overall_milestone_percent(total, done):
	if not total:
		return 0
	return round(done / total * 100)


def forwarding_milestone_progress_map(job_names):
	"""Bulk {job_name: overall_milestone_percent} for list endpoints."""
	if not job_names:
		return {}

	counts = {name: {"total": 0, "done": 0} for name in job_names}

	for fieldname in MILESTONE_TABLE_FIELDS:
		rows = frappe.db.sql(
			"""
			SELECT parent, COUNT(*) AS total, SUM(IFNULL(is_completed, 0)) AS done
			FROM `tabJob Milestone Progress`
			WHERE parenttype = 'Forwarding Job' AND parentfield = %(field)s AND parent IN %(names)s
			GROUP BY parent
			""",
			{"field": fieldname, "names": tuple(job_names)},
			as_dict=True,
		)
		for row in rows:
			bucket = counts[row.parent]
			bucket["total"] += row.total or 0
			bucket["done"] += int(row.done or 0)

	parcels = frappe.db.sql(
		"""
		SELECT
			parent, cargo_type, is_truck_required, to_be_returned,
			is_booked, is_loaded, is_offloaded, is_completed,
			is_returned, empty_return_date, discharge_date, gate_out_date
		FROM `tabCargo Parcel Details`
		WHERE parenttype = 'Forwarding Job' AND parent IN %(names)s
		""",
		{"names": tuple(job_names)},
		as_dict=True,
	)
	parcels_by_job = {}
	for parcel in parcels:
		parcels_by_job.setdefault(parcel.parent, []).append(parcel)

	jobs = frappe.get_all(
		"Forwarding Job",
		filters={"name": ["in", job_names]},
		fields=["name", "requires_sea_air_freight", "atd", "ata"],
	)
	jobs_by_name = {job.name: job for job in jobs}

	for name in job_names:
		job_parcels = parcels_by_job.get(name, [])
		rt_total, rt_done = road_transport_progress_counts(job_parcels)
		counts[name]["total"] += rt_total
		counts[name]["done"] += rt_done

		job = jobs_by_name.get(name) or {}
		if job.get("requires_sea_air_freight"):
			sa_total, sa_done = sea_air_progress_counts(job, job_parcels)
			counts[name]["total"] += sa_total
			counts[name]["done"] += sa_done

	return {
		name: overall_milestone_percent(bucket["total"], bucket["done"])
		for name, bucket in counts.items()
	}
