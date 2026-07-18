# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Read-only API layer backing the Clearing module of the Command Center.

Reads from Clearing Job + its child tables and linked Sales/Purchase Invoices.
Mirrors the Forwarding shipment_dashboard controller so the Vue SPA can bind to
a uniform set of verbs (get_overview / get_jobs / get_job_detail /
get_finance_summary / exports). Clearing stores its milestones as checkbox+date
pairs directly on the job (not Job Milestone Progress child tables), so progress
is computed from those here.
"""

import frappe
from frappe.utils import flt, getdate, nowdate

from freightmas.utils.permissions import check_freightmas_role, check_doc_read_permission
from freightmas.utils.dashboard_common import monthly_revenue_margin_trend
# Reuse the Excel workbook helpers already written for the Forwarding dashboard.
from freightmas.freightmas.page.shipment_dashboard.shipment_dashboard import (
	_write_sheet,
	_send_workbook,
	_timestamped,
)

NOT_ACTIVE_STATUSES = ["Completed", "Closed", "Cancelled"]

# Ordered milestone chain for a clearing job: (checkbox, date, label). Progress
# percent = completed checkboxes / total. Import-oriented (the common case);
# export vessel-loading checkboxes are included so they count when set.
CLEARING_MILESTONES = [
	("is_bl_received", "bl_received_date", "BL Received"),
	("is_bl_confirmed", "bl_confirmed_date", "BL Confirmed"),
	("is_booking_confirmed", "booking_confirmation_date", "Booking Confirmed"),
	("is_vessel_arrived_at_port", "vessel_arrived_date", "Vessel Arrived"),
	("is_sl_invoice_received", "sl_invoice_received_date", "SL Invoice Received"),
	("is_sl_invoice_paid", "sl_invoice_payment_date", "SL Invoice Paid"),
	("is_do_requested", "do_requested_date", "DO Requested"),
	("is_do_received", "do_received_date", "DO Received"),
	("is_discharged_from_port", "discharge_date", "Discharged from Port"),
	("is_clearing_for_shipment_done", "shipment_cleared_date", "Clearing Done"),
	("is_port_release_confirmed", "port_release_confirmed_date", "Port Release Confirmed"),
]

_CHECK_FIELDS = [m[0] for m in CLEARING_MILESTONES]


# ============================================================
# OVERVIEW
# ============================================================

@frappe.whitelist()
def get_overview():
	check_freightmas_role()
	today = nowdate()
	statuses = tuple(NOT_ACTIVE_STATUSES)

	active_count = frappe.db.count(
		"Clearing Job", {"docstatus": ["<", 2], "status": ["not in", NOT_ACTIVE_STATUSES]}
	)

	awaiting_bl = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabClearing Job`
		   WHERE docstatus < 2 AND status NOT IN %(st)s
		     AND (IFNULL(is_bl_received, 0) = 0 OR IFNULL(is_bl_confirmed, 0) = 0)""",
		{"st": statuses},
	)[0][0]

	do_pending = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabClearing Job`
		   WHERE docstatus < 2 AND status NOT IN %(st)s
		     AND IFNULL(is_do_requested, 0) = 1 AND IFNULL(is_do_received, 0) = 0""",
		{"st": statuses},
	)[0][0]

	awaiting_release = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabClearing Job`
		   WHERE docstatus < 2 AND status NOT IN %(st)s
		     AND IFNULL(is_discharged_from_port, 0) = 1
		     AND IFNULL(is_port_release_confirmed, 0) = 0""",
		{"st": statuses},
	)[0][0]

	vessel_overdue = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabClearing Job`
		   WHERE docstatus < 2 AND status NOT IN %(st)s
		     AND eta < %(today)s AND ata IS NULL""",
		{"st": statuses, "today": today},
	)[0][0]

	uninvoiced_jobs = frappe.db.sql(
		"""SELECT COUNT(DISTINCT parent) FROM `tabClearing Revenue Charges`
		   WHERE parenttype = 'Clearing Job' AND IFNULL(is_invoiced, 0) = 0
		     AND parent IN (SELECT name FROM `tabClearing Job`
		                    WHERE docstatus < 2 AND status NOT IN %(st)s)""",
		{"st": statuses},
	)[0][0]

	jobs_by_status = frappe.db.sql(
		"""SELECT status, COUNT(*) AS count FROM `tabClearing Job`
		   WHERE docstatus < 2 GROUP BY status
		   ORDER BY FIELD(status, 'Draft', 'In Progress', 'Delivered', 'Completed', 'Closed', 'Cancelled')""",
		as_dict=True,
	)

	top_customers = frappe.db.sql(
		"""SELECT customer, COUNT(*) AS job_count FROM `tabClearing Job`
		   WHERE docstatus < 2 AND status NOT IN %(st)s
		   GROUP BY customer ORDER BY job_count DESC LIMIT 5""",
		{"st": statuses}, as_dict=True,
	)

	top_corridors = frappe.db.sql(
		"""SELECT origin, destination, COUNT(*) AS job_count FROM `tabClearing Job`
		   WHERE docstatus < 2 AND status NOT IN %(st)s
		     AND origin IS NOT NULL AND destination IS NOT NULL
		   GROUP BY origin, destination ORDER BY job_count DESC LIMIT 5""",
		{"st": statuses}, as_dict=True,
	)

	blockers = frappe.get_all(
		"Clearing Job",
		filters={"docstatus": ["<", 2], "status": ["not in", NOT_ACTIVE_STATUSES],
		         "current_comment": ["is", "set"]},
		fields=["name", "customer", "status", "current_comment", "last_updated_on"],
		order_by="last_updated_on desc", limit_page_length=8,
	)

	return {
		"kpis": {
			"active_jobs": active_count,
			"awaiting_bl": awaiting_bl,
			"do_pending": do_pending,
			"awaiting_release": awaiting_release,
			"vessel_overdue": vessel_overdue,
			"uninvoiced_jobs": uninvoiced_jobs,
		},
		"jobs_by_status": jobs_by_status,
		"monthly_trend": monthly_revenue_margin_trend("Clearing Job", months=6),
		"top_customers": top_customers,
		"top_corridors": top_corridors,
		"recent_blockers": blockers,
	}


def _milestone_percent(job):
	total = len(_CHECK_FIELDS)
	done = sum(1 for f in _CHECK_FIELDS if job.get(f))
	return round(done / total * 100) if total else 0


# ============================================================
# JOBS (list)
# ============================================================

@frappe.whitelist()
def get_jobs(customer=None, status=None, direction=None, search=None, limit_start=0, limit_page_length=20):
	check_freightmas_role()

	filters = {"docstatus": ["<", 2]}
	if customer:
		filters["customer"] = customer
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

	fields = [
		"name", "customer", "customer_reference", "direction", "status",
		"origin", "destination", "shipping_line", "bl_number", "bl_type",
		"eta", "ata", "discharge_date", "current_comment", "last_updated_on",
	] + _CHECK_FIELDS

	jobs = frappe.get_list(
		"Clearing Job", filters=filters, or_filters=or_filters, fields=fields,
		order_by="modified desc",
		limit_start=frappe.utils.cint(limit_start),
		limit_page_length=frappe.utils.cint(limit_page_length),
	)

	total_count = frappe.db.count("Clearing Job", filters=filters)
	today = getdate(nowdate())
	for j in jobs:
		j["milestone_percent"] = _milestone_percent(j)
		j["is_overdue"] = bool(j.eta and getdate(j.eta) < today and not j.ata)
		# Drop the raw checkbox fields from the payload - only the percent matters.
		for f in _CHECK_FIELDS:
			j.pop(f, None)

	return {"jobs": jobs, "total_count": total_count}


# ============================================================
# JOB DETAIL
# ============================================================

@frappe.whitelist()
def get_job_detail(job_name):
	check_freightmas_role()
	check_doc_read_permission("Clearing Job", job_name)

	doc = frappe.get_doc("Clearing Job", job_name)

	header = {
		"name": doc.name,
		"customer": doc.customer,
		"customer_reference": doc.customer_reference,
		"consignee": doc.consignee,
		"direction": doc.direction,
		"status": doc.status,
		"origin": doc.origin,
		"destination": doc.destination,
		"shipping_line": doc.shipping_line,
		"bl_number": doc.bl_number,
		"bl_type": doc.bl_type,
		"is_bl_received": doc.is_bl_received,
		"is_bl_confirmed": doc.is_bl_confirmed,
		"currency": doc.currency,
		"current_comment": doc.current_comment,
		"last_updated_on": doc.last_updated_on,
		"last_updated_by": doc.last_updated_by,
	}

	shipment_dates = {
		"eta": doc.eta,
		"ata": doc.ata,
		"etd": doc.etd,
		"atd": doc.atd,
		"discharge_date": doc.discharge_date,
		"dnd_start_date": doc.dnd_start_date,
		"storage_start_date": doc.storage_start_date,
		"completed_on": doc.completed_on,
	}

	milestones = [
		{
			"label": label,
			"is_completed": bool(doc.get(check)),
			"completed_on": doc.get(date_field),
		}
		for check, date_field, label in CLEARING_MILESTONES
	]

	cargo = [
		{
			"container_number": r.container_number or r.cargo_item_description,
			"container_type": r.container_type,
			"cargo_type": r.cargo_type,
			"to_be_returned": bool(r.to_be_returned),
			"is_loaded": bool(r.is_loaded),
			"is_returned": bool(r.is_returned),
			"discharge_date": r.discharge_date,
			"gate_out_full_date": r.gate_out_full_date,
			"api_container_status": r.api_container_status,
		}
		for r in (doc.get("cargo_package_details") or [])
	]

	tracking = [
		{
			"comment": r.comment,
			"source": r.source,
			"updated_on": r.updated_on,
			"updated_by": r.updated_by_name or r.updated_by,
		}
		for r in sorted(doc.get("clearing_tracking") or [], key=lambda r: r.idx or 0, reverse=True)
	][:15]

	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"clearing_job_reference": doc.name, "docstatus": ["<", 2]},
		fields=["name", "customer", "posting_date", "due_date", "grand_total", "outstanding_amount", "status"],
	)
	purchase_invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"clearing_job_reference": doc.name, "docstatus": ["<", 2]},
		fields=["name", "supplier", "posting_date", "due_date", "grand_total", "outstanding_amount", "status"],
	)

	finance = doc.get_job_totals_summary()

	return {
		"header": header,
		"shipment_dates": shipment_dates,
		"milestones": milestones,
		"cargo": cargo,
		"tracking": tracking,
		"sales_invoices": invoices,
		"purchase_invoices": purchase_invoices,
		"finance": finance,
	}


# ============================================================
# FINANCE
# ============================================================

@frappe.whitelist()
def get_finance_summary(from_date=None, to_date=None, customer=None):
	check_freightmas_role()

	conditions = ["cj.docstatus = 1", "cj.status != 'Cancelled'"]
	values = {}
	if from_date:
		conditions.append("cj.creation >= %(from_date)s")
		values["from_date"] = from_date
	if to_date:
		conditions.append("cj.creation <= %(to_date)s")
		values["to_date"] = to_date
	if customer:
		conditions.append("cj.customer = %(customer)s")
		values["customer"] = customer

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			cj.name, cj.customer, cj.status,
			cj.total_quoted_revenue_base AS quoted_revenue,
			cj.total_quoted_cost_base AS quoted_cost,
			cj.total_working_revenue_base AS working_revenue,
			cj.total_working_cost AS working_cost,
			COALESCE(si.invoiced_revenue, 0) AS invoiced_revenue,
			COALESCE(pi.invoiced_cost, 0) AS invoiced_cost
		FROM `tabClearing Job` cj
		LEFT JOIN (
			SELECT clearing_job_reference, SUM(grand_total) AS invoiced_revenue
			FROM `tabSales Invoice`
			WHERE docstatus = 1 AND clearing_job_reference IS NOT NULL
			GROUP BY clearing_job_reference
		) si ON si.clearing_job_reference = cj.name
		LEFT JOIN (
			SELECT clearing_job_reference, SUM(grand_total) AS invoiced_cost
			FROM `tabPurchase Invoice`
			WHERE docstatus = 1 AND clearing_job_reference IS NOT NULL
			GROUP BY clearing_job_reference
		) pi ON pi.clearing_job_reference = cj.name
		WHERE {where}
		ORDER BY cj.creation DESC LIMIT 200
		""",
		values, as_dict=True,
	)

	totals = {"quoted_revenue": 0, "quoted_cost": 0, "working_revenue": 0,
	          "working_cost": 0, "invoiced_revenue": 0, "invoiced_cost": 0}
	for r in rows:
		r["invoiced_profit"] = flt(r.invoiced_revenue) - flt(r.invoiced_cost)
		r["invoiced_margin_percent"] = flt(r.invoiced_profit / r.invoiced_revenue * 100, 2) if r.invoiced_revenue else 0
		for k in totals:
			totals[k] += flt(r.get(k) or 0)

	totals["quoted_profit"] = flt(totals["quoted_revenue"] - totals["quoted_cost"], 2)
	totals["working_profit"] = flt(totals["working_revenue"] - totals["working_cost"], 2)
	totals["invoiced_profit"] = flt(totals["invoiced_revenue"] - totals["invoiced_cost"], 2)
	totals["invoiced_margin_percent"] = flt(
		totals["invoiced_profit"] / totals["invoiced_revenue"] * 100, 2
	) if totals["invoiced_revenue"] else 0

	outstanding_sales = frappe.db.sql(
		"""SELECT name, customer, posting_date, due_date, grand_total, outstanding_amount
		   FROM `tabSales Invoice`
		   WHERE docstatus = 1 AND outstanding_amount > 0 AND clearing_job_reference IS NOT NULL
		   ORDER BY due_date ASC LIMIT 20""",
		as_dict=True,
	)

	return {
		"jobs": rows,
		"totals": totals,
		"outstanding_sales_invoices": outstanding_sales,
		"monthly_trend": monthly_revenue_margin_trend("Clearing Job", months=12),
	}


# ============================================================
# EXCEL EXPORTS
# ============================================================

@frappe.whitelist()
def export_jobs(customer=None, status=None, direction=None, search=None):
	check_freightmas_role()
	import openpyxl

	res = get_jobs(customer=customer, status=status, direction=direction, search=search,
	               limit_start=0, limit_page_length=5000)
	columns = [
		{"label": "Job", "fieldname": "name"},
		{"label": "Customer", "fieldname": "customer"},
		{"label": "Reference", "fieldname": "customer_reference"},
		{"label": "Direction", "fieldname": "direction"},
		{"label": "Origin", "fieldname": "origin"},
		{"label": "Destination", "fieldname": "destination"},
		{"label": "Shipping Line", "fieldname": "shipping_line"},
		{"label": "BL Number", "fieldname": "bl_number"},
		{"label": "ETA", "fieldname": "eta", "fieldtype": "Date"},
		{"label": "ATA", "fieldname": "ata", "fieldtype": "Date"},
		{"label": "Status", "fieldname": "status"},
		{"label": "Milestone %", "fieldname": "milestone_percent", "fieldtype": "Float"},
	]
	wb = openpyxl.Workbook()
	_write_sheet(wb.active, "Clearing Jobs", columns, res["jobs"])
	_send_workbook(wb, _timestamped("Clearing_Jobs"))


@frappe.whitelist()
def export_finance(from_date=None, to_date=None, customer=None):
	check_freightmas_role()
	import openpyxl

	res = get_finance_summary(from_date=from_date, to_date=to_date, customer=customer)
	columns = [
		{"label": "Job", "fieldname": "name"},
		{"label": "Customer", "fieldname": "customer"},
		{"label": "Status", "fieldname": "status"},
		{"label": "Quoted Revenue", "fieldname": "quoted_revenue", "fieldtype": "Currency"},
		{"label": "Quoted Cost", "fieldname": "quoted_cost", "fieldtype": "Currency"},
		{"label": "Working Revenue", "fieldname": "working_revenue", "fieldtype": "Currency"},
		{"label": "Working Cost", "fieldname": "working_cost", "fieldtype": "Currency"},
		{"label": "Invoiced Revenue", "fieldname": "invoiced_revenue", "fieldtype": "Currency"},
		{"label": "Invoiced Cost", "fieldname": "invoiced_cost", "fieldtype": "Currency"},
		{"label": "Invoiced Profit", "fieldname": "invoiced_profit", "fieldtype": "Currency"},
		{"label": "Invoiced Margin %", "fieldname": "invoiced_margin_percent", "fieldtype": "Float"},
	]
	wb = openpyxl.Workbook()
	_write_sheet(wb.active, "Clearing Finance", columns, res["jobs"])
	_send_workbook(wb, _timestamped("Clearing_Finance"))
