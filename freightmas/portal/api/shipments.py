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
from frappe.utils import formatdate, getdate, now_datetime, nowdate

from freightmas.freightmas.report.report_export_utils import send_excel_response
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

# Milestone tables shown as their own "Milestones" columns in the tracking
# report - each is job-level (Job Milestone Progress), not per-container, so
# its value repeats identically on every container row of that job.
REPORT_MILESTONE_TABLES = {
	"port_clearance_milestones": "requires_port_clearance",
	"border_clearance_milestones": "requires_border_clearance",
	"warehouse_milestones": "requires_warehousing",
}

# Port/Border/Warehouse Clearance are job/BL-level facts (Job Milestone
# Progress is a child table on Forwarding Job, not on Cargo Parcel Details) -
# they belong on a job's own row. Trucking and Completed On Date are the
# only genuinely per-container facts - they belong on that container's own
# row. Both row kinds share one flat table/column set (see
# _build_tracking_workbook): a job's row populates the "job" columns and
# leaves the "container" columns blank, its container rows do the reverse,
# and Excel row-grouping (outline_level) makes the container rows collapse
# under their job - one cohesive table, no repeated BL-level values.
REPORT_COLUMNS = [
	# "both": Job ID is written on every row (job row AND its container rows)
	# as the structural/visual key tying container rows back to their job.
	{"label": "Job ID", "fieldname": "job_id", "level": "both"},
	{"label": "Consignee", "fieldname": "consignee", "level": "job"},
	{"label": "Customer Reference", "fieldname": "customer_reference", "level": "job"},
	{"label": "BL Number", "fieldname": "bl_number", "level": "job"},
	{"label": "Cargo Count", "fieldname": "cargo_count", "level": "job"},
	{"label": "Port Clearance Milestones", "fieldname": "port_clearance_milestones", "level": "job"},
	{"label": "Border Clearance Milestones", "fieldname": "border_clearance_milestones", "level": "job"},
	{"label": "Warehouse Milestones", "fieldname": "warehouse_milestones", "level": "job"},
	{"label": "Latest Loading Comment", "fieldname": "latest_loading_comment", "level": "job"},
	{"label": "Container Number", "fieldname": "container_number", "level": "container"},
	{"label": "Container Type", "fieldname": "container_type", "level": "container"},
	{"label": "Trucking Milestones", "fieldname": "trucking_milestones", "level": "container"},
	{"label": "Completed On Date", "fieldname": "completed_on_date", "fieldtype": "Date", "level": "container"},
]


def _caller_customer_filter():
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			_("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)
	return customers


def _job_list_filters(customers, status=None, direction=None, search=None):
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
	return filters, or_filters


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

	filters, or_filters = _job_list_filters(customers, status, direction, search)

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


def _cargo_count_summary(cargo_rows):
	"""Mirror forwarding_job.js's update_cargo_count_forwarding grouping:
	containerised rows grouped by container_type (qty summed), everything
	else summed into one "General Cargo" bucket."""
	grouped = {}
	general_qty = 0
	for c in cargo_rows:
		if c.cargo_type == "Containerised":
			key = c.container_type or "Unknown"
			grouped[key] = grouped.get(key, 0) + (c.cargo_quantity or 0)
		else:
			general_qty += c.cargo_quantity or 0

	parts = []
	if grouped:
		parts.append(", ".join(f"{qty}x{ctype}" for ctype, qty in grouped.items()))
	if general_qty:
		parts.append(f"{general_qty} General Cargo")
	return " + ".join(parts)


def _latest_milestone_label(rows):
	"""Rows are ordered by idx (checklist sequence) - return the label/date of
	the furthest-progressed completed milestone, blank if none completed."""
	latest = None
	for r in rows:
		if r.is_completed:
			latest = r
	if not latest:
		return ""
	if latest.completed_on:
		return f"{latest.milestone_label} ({formatdate(latest.completed_on, 'dd-MMM-yy')})"
	return latest.milestone_label


TRUCKING_STAGES = [
	("is_completed", "completed_on_date", "Completed"),
	("is_returned", "returned_on_date", "Returned"),
	("is_offloaded", "offloaded_on_date", "Offloaded"),
	("is_loaded", "loaded_on_date", "Loaded"),
	("is_booked", "booked_on_date", "Booked"),
]


def _trucking_stage(cargo_row):
	"""Furthest-progressed trucking stage for one container, e.g. "Loaded (15-Jul-26)"."""
	for flag, date_field, label in TRUCKING_STAGES:
		if cargo_row.get(flag):
			date_value = cargo_row.get(date_field)
			if date_value:
				return f"{label} ({formatdate(date_value, 'dd-MMM-yy')})"
			return label
	return ""


def _build_tracking_workbook(columns, rows):
	"""Compact single-sheet workbook, one flat table: each job gets one bold
	summary row (populating the "job"-level columns, e.g. Port/Border/
	Warehouse Milestones), immediately followed by that job's container rows
	(populating the "container"-level columns, e.g. Trucking Milestones) -
	grouped via Excel's row outline/grouping so the container rows collapse
	under their job's row (a +/- control in the row gutter), keeping
	everything as one cohesive table without repeating job-level values on
	every container row. Each row dict must carry a "_level" key of "job" or
	"container" saying which columns it populates. Same underlying
	formatting conventions as report_export_utils.build_excel_file (dd-MMM-yy
	dates, left/right alignment, auto-fit column widths, hidden gridlines).
	"""
	import io

	from openpyxl import Workbook
	from openpyxl.styles import Alignment, Font, PatternFill
	from openpyxl.utils import get_column_letter

	wb = Workbook()
	ws = wb.active
	ws.title = "Tracking Report"

	job_row_font = Font(bold=True)
	job_row_fill = PatternFill("solid", fgColor="D6DCE4")
	header_font = Font(bold=True, color="FFFFFF")
	header_fill = PatternFill("solid", fgColor="305496")
	left_align = Alignment(horizontal="left", vertical="center")
	right_align = Alignment(horizontal="right", vertical="center")

	ncols = len(columns)
	for col_idx, col in enumerate(columns, 1):
		cell = ws.cell(row=1, column=col_idx, value=col["label"])
		cell.font = header_font
		cell.fill = header_fill
		cell.alignment = left_align

	ws.freeze_panes = "A2"

	for row_offset, row_data in enumerate(rows):
		row_idx = row_offset + 2
		is_job_row = row_data.get("_level") == "job"

		for col_idx, col in enumerate(columns, 1):
			if col["level"] not in ("both", row_data["_level"]):
				continue  # blank on this row - belongs to the other granularity

			fieldname = col["fieldname"]
			fieldtype = col.get("fieldtype")
			value = row_data.get(fieldname)
			is_numeric = fieldtype in ("Int", "Float", "Currency")
			cell = ws.cell(row=row_idx, column=col_idx)

			if fieldtype == "Date" and value:
				cell.value = formatdate(value, "dd-MMM-yy")
			elif is_numeric:
				cell.value = value or 0
			else:
				cell.value = value or ""

			cell.alignment = right_align if is_numeric else left_align
			if is_job_row:
				cell.font = job_row_font
				cell.fill = job_row_fill

		if not is_job_row:
			ws.row_dimensions[row_idx].outline_level = 1

	# Collapse control sits above its detail rows (job row first, containers
	# collapse underneath), not Excel's default "total row after detail".
	ws.sheet_properties.outlinePr.summaryBelow = False

	for col_idx in range(1, ncols + 1):
		max_length = 0
		for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
			for cell in row:
				length = len(str(cell.value)) if cell.value else 0
				max_length = max(max_length, length)
		ws.column_dimensions[get_column_letter(col_idx)].width = max(10, min(max_length + 2, 40))

	ws.sheet_view.showGridLines = False

	output = io.BytesIO()
	wb.save(output)
	output.seek(0)
	return output.getvalue()


@frappe.whitelist()
def export_tracking_report(status=None, direction=None, search=None):
	check_portal_access()
	customers = _caller_customer_filter()

	filters, or_filters = _job_list_filters(customers, status, direction, search)

	jobs = frappe.get_all(
		"Forwarding Job",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "customer_reference", "consignee", "bl_number", "current_comment",
			"requires_port_clearance", "requires_border_clearance", "requires_warehousing",
		],
		order_by="modified desc",
	)
	job_names = [j.name for j in jobs]

	customer_name_map = {}
	consignee_names = list({j.consignee for j in jobs if j.consignee})
	if consignee_names:
		customer_name_map = {
			c.name: c.customer_name
			for c in frappe.get_all(
				"Customer", filters={"name": ["in", consignee_names]}, fields=["name", "customer_name"]
			)
		}

	cargo_by_job = {}
	milestone_by_job = {fieldname: {} for fieldname in REPORT_MILESTONE_TABLES}

	if job_names:
		cargo_rows = frappe.get_all(
			"Cargo Parcel Details",
			filters={"parenttype": "Forwarding Job", "parent": ["in", job_names]},
			fields=[
				"parent", "container_number", "container_type", "cargo_type", "cargo_quantity",
				"is_booked", "booked_on_date", "is_loaded", "loaded_on_date",
				"is_offloaded", "offloaded_on_date", "is_returned", "returned_on_date",
				"is_completed", "completed_on_date",
			],
			order_by="parent, idx",
		)
		for r in cargo_rows:
			cargo_by_job.setdefault(r.parent, []).append(r)

		for fieldname in REPORT_MILESTONE_TABLES:
			rows = frappe.get_all(
				"Job Milestone Progress",
				filters={
					"parenttype": "Forwarding Job", "parentfield": fieldname,
					"parent": ["in", job_names],
				},
				fields=["parent", "milestone_label", "is_completed", "completed_on"],
				order_by="parent, idx",
			)
			for r in rows:
				milestone_by_job[fieldname].setdefault(r.parent, []).append(r)

	report_rows = []
	for job in jobs:
		containers = cargo_by_job.get(job.name, [])

		job_row = {
			"_level": "job",
			"job_id": job.name,
			"consignee": customer_name_map.get(job.consignee, job.consignee),
			"customer_reference": job.customer_reference,
			"bl_number": job.bl_number,
			"cargo_count": _cargo_count_summary(containers),
			"latest_loading_comment": job.current_comment,
		}
		for fieldname, requires_field in REPORT_MILESTONE_TABLES.items():
			job_row[fieldname] = (
				_latest_milestone_label(milestone_by_job[fieldname].get(job.name, []))
				if job.get(requires_field)
				else ""
			)
		report_rows.append(job_row)

		for c in containers:
			report_rows.append({
				"_level": "container",
				"job_id": job.name,
				"container_number": c.container_number,
				"container_type": c.container_type,
				"trucking_milestones": _trucking_stage(c),
				"completed_on_date": c.completed_on_date,
			})

	file_bytes = _build_tracking_workbook(REPORT_COLUMNS, report_rows)
	filename = f"Tracking_Report_{now_datetime().strftime('%Y%m%d_%H%M')}.xlsx"
	send_excel_response(file_bytes, filename)

	log_portal_access("export_tracking_report", doctype="Forwarding Job")
