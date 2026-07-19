# Client Portal read API: Forwarding Job list + detail + tracking.
#
# Mirrors the query idiom of freightmas.freightmas.page.shipment_dashboard.
# shipment_dashboard (SQL join / milestone-percent aggregation style) but
# is re-implemented rather than called directly: that module is gated by
# check_freightmas_role() and returns every customer's data (including
# WIP/margin fields), and there is no safe way to parameterize it to one
# Customer without changing its gate - which would weaken the internal
# dashboard. Every field returned here has been hand-picked to exclude
# costing/margin data.

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from freightmas.portal.security import (
	assert_customer_scope,
	check_portal_access,
	get_portal_customer_names,
	log_portal_access,
)

NOT_ACTIVE_STATUSES = ["Completed", "Closed", "Cancelled"]

JOB_LIST_FIELDS = [
	"name", "customer_reference", "direction", "shipment_mode", "shipment_type",
	"status", "port_of_loading", "port_of_discharge", "destination",
	"vessel_flight_no", "bl_number", "cargo_count", "eta", "ata", "etd", "atd",
	"discharge_date", "current_comment", "last_updated_on",
]

MILESTONE_TABLE_FIELDS = [
	"road_freight_milestones",
	"port_clearance_milestones",
	"border_clearance_milestones",
	"warehouse_milestones",
]


def _caller_customer_filter():
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			_("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)
	return customers


def _milestone_progress_map(job_names):
	if not job_names:
		return {}

	counts = {}
	for fieldname in MILESTONE_TABLE_FIELDS:
		rows = frappe.db.sql(
			"""
			SELECT parent, COUNT(*) AS total, SUM(IFNULL(is_completed, 0)) AS done
			FROM `tabJob Milestone Progress`
			WHERE parenttype = 'Forwarding Job' AND parentfield = %(field)s AND parent IN %(names)s
			GROUP BY parent
			""",
			{"field": fieldname, "names": job_names},
			as_dict=True,
		)
		for r in rows:
			bucket = counts.setdefault(r.parent, {"total": 0, "done": 0})
			bucket["total"] += r.total or 0
			bucket["done"] += int(r.done or 0)

	return {
		name: (round(v["done"] / v["total"] * 100) if v["total"] else 0)
		for name, v in counts.items()
	}


@frappe.whitelist()
def get_jobs(status=None, direction=None, search=None, limit_start=0, limit_page_length=20):
	check_portal_access()
	customers = _caller_customer_filter()

	filters = {"docstatus": ["<", 2], "customer": ["in", customers]}
	if status:
		filters["status"] = status
	if direction:
		filters["direction"] = direction

	or_filters = None
	if search:
		or_filters = [
			["name", "like", f"%{search}%"],
			["customer_reference", "like", f"%{search}%"],
			["bl_number", "like", f"%{search}%"],
		]

	# get_all(), not get_list(): Customer Portal User holds zero DocType
	# permissions by design (see freightmas/portal/security.py) - the
	# explicit `customer` filter above is the actual access boundary, not
	# Frappe's own permission system, so it must not be re-checked here.
	jobs = frappe.get_all(
		"Forwarding Job",
		filters=filters,
		or_filters=or_filters,
		fields=JOB_LIST_FIELDS,
		order_by="modified desc",
		limit_start=frappe.utils.cint(limit_start),
		limit_page_length=frappe.utils.cint(limit_page_length),
	)

	total_count = frappe.db.count("Forwarding Job", filters=filters)

	progress_map = _milestone_progress_map([j.name for j in jobs])
	today = getdate(nowdate())
	for j in jobs:
		j["milestone_percent"] = progress_map.get(j.name, 0)
		j["is_overdue"] = bool(
			(j.direction == "Import" and j.eta and getdate(j.eta) < today and not j.ata)
			or (j.direction == "Export" and j.etd and getdate(j.etd) < today and not j.atd)
		)

	log_portal_access("list_shipments", doctype="Forwarding Job")

	return {"jobs": jobs, "total_count": total_count}


@frappe.whitelist()
def get_job_detail(job_name):
	check_portal_access()
	customer = assert_customer_scope("Forwarding Job", job_name, "customer")

	doc = frappe.get_doc("Forwarding Job", job_name)

	header = {
		"name": doc.name,
		"customer_reference": doc.customer_reference,
		"consignee": doc.consignee,
		"direction": doc.direction,
		"shipment_mode": doc.shipment_mode,
		"shipment_type": doc.shipment_type,
		"status": doc.status,
		"port_of_loading": doc.port_of_loading,
		"port_of_discharge": doc.port_of_discharge,
		"destination": doc.destination,
		"vessel_flight_no": doc.vessel_flight_no,
		"vessel_flight_date": doc.vessel_flight_date,
		"bl_number": doc.bl_number,
		"is_bl_received": doc.is_bl_received,
		"cargo_description": doc.cargo_description,
		"cargo_count": doc.cargo_count,
		"incoterms": doc.incoterms,
		"current_comment": doc.current_comment,
		"last_updated_on": doc.last_updated_on,
	}

	shipment_dates = {
		"booking_date": doc.booking_date,
		"cargo_ready_date": doc.cargo_ready_date,
		"etd": doc.etd,
		"atd": doc.atd,
		"eta": doc.eta,
		"ata": doc.ata,
		"discharge_date": doc.discharge_date,
		"completed_on": doc.completed_on,
	}

	milestone_stages = []
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
	for fieldname, label in section_labels.items():
		if not requires_map.get(fieldname):
			continue
		rows = doc.get(fieldname) or []
		if not rows:
			continue
		milestone_stages.append(
			{
				"group": label,
				"milestones": [
					{
						"label": r.milestone_label,
						"is_completed": bool(r.is_completed),
						"completed_on": r.completed_on,
					}
					for r in rows
				],
			}
		)

	cargo = [
		{
			"name": r.name,
			"container_number": r.container_number or r.cargo_item_description,
			"container_type": r.container_type,
			"cargo_type": r.cargo_type,
			"cargo_quantity": r.cargo_quantity,
			"cargo_uom": r.cargo_uom,
			"is_hazardous": bool(r.is_hazardous),
			"is_booked": bool(r.is_booked),
			"is_loaded": bool(r.is_loaded),
			"is_offloaded": bool(r.is_offloaded),
			"is_returned": bool(r.is_returned),
			"is_completed": bool(r.is_completed),
			"truck_location": r.truck_location,
			"tracking_comment": r.tracking_comment,
			"updated_on": r.updated_on,
		}
		for r in (doc.cargo_parcel_details or [])
	]

	tracking = [
		{
			"event": r.event,
			"date": r.date,
			"source": r.source,
		}
		for r in sorted(doc.get("tracking_timeline") or [], key=lambda r: r.idx or 0, reverse=True)
	][:15]

	log_portal_access("view_shipment", doctype="Forwarding Job", docname=job_name, customer=customer)

	return {
		"header": header,
		"shipment_dates": shipment_dates,
		"milestone_stages": milestone_stages,
		"cargo": cargo,
		"tracking": tracking,
	}
