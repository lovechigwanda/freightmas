# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Read-only API layer backing the Shipment Dashboard (Vue SPA).

No new doctypes/schema - every endpoint here reads from Forwarding Job and
its existing child tables / linked Sales & Purchase Invoices. Kept entirely
separate from the Forwarding Job controller so it can evolve independently
of the form's own whitelisted methods.
"""

from io import BytesIO

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_months, get_first_day, get_last_day, formatdate

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from freightmas.utils.permissions import check_freightmas_role, check_doc_read_permission

NOT_ACTIVE_STATUSES = ["Completed", "Closed", "Cancelled"]

MILESTONE_TABLE_FIELDS = [
	"road_freight_milestones",
	"port_clearance_milestones",
	"border_clearance_milestones",
	"warehouse_milestones",
]


# ============================================================
# BRANDING
# ============================================================

@frappe.whitelist()
def get_branding():
	check_freightmas_role()

	company = frappe.defaults.get_global_default("company") or frappe.defaults.get_user_default("Company")
	if not company:
		return {"company": None, "company_name": "FreightMas", "logo": None}

	info = frappe.db.get_value(
		"Company",
		company,
		["company_name", "company_logo", "phone_no", "email", "tax_id", "default_currency"],
		as_dict=True,
	) or {}

	address_line = ""
	address = frappe.get_all(
		"Address",
		filters={"link_doctype": "Company", "link_name": company},
		fields=["address_line1", "address_line2", "city", "country"],
		limit=1,
	)
	if address:
		a = address[0]
		parts = [p for p in [a.address_line1, a.address_line2, a.city, a.country] if p]
		address_line = ", ".join(parts)

	return {
		"company": company,
		"company_name": info.get("company_name") or company,
		"logo": info.get("company_logo"),
		"phone": info.get("phone_no"),
		"email": info.get("email"),
		"tax_id": info.get("tax_id"),
		"address": address_line,
		"currency": info.get("default_currency"),
	}


# ============================================================
# OVERVIEW
# ============================================================

@frappe.whitelist()
def get_overview():
	check_freightmas_role()
	today = nowdate()

	active_count = frappe.db.count(
		"Forwarding Job",
		{"docstatus": ["<", 2], "status": ["not in", NOT_ACTIVE_STATUSES]},
	)

	overdue_arrivals = frappe.db.count(
		"Forwarding Job",
		{
			"docstatus": ["<", 2],
			"status": ["not in", NOT_ACTIVE_STATUSES],
			"direction": "Import",
			"eta": ["<", today],
			"ata": ["is", "not set"],
		},
	)

	overdue_departures = frappe.db.count(
		"Forwarding Job",
		{
			"docstatus": ["<", 2],
			"status": ["not in", NOT_ACTIVE_STATUSES],
			"direction": "Export",
			"etd": ["<", today],
			"atd": ["is", "not set"],
		},
	)

	missing_bl = frappe.db.sql(
		"""
		SELECT COUNT(*) FROM `tabForwarding Job`
		WHERE docstatus < 2 AND status NOT IN %(statuses)s
		  AND (IFNULL(bl_number, '') = '' OR IFNULL(is_bl_received, 0) = 0 OR IFNULL(is_bl_confirmed, 0) = 0)
		""",
		{"statuses": NOT_ACTIVE_STATUSES},
	)[0][0]

	uninvoiced_jobs = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT parent) FROM `tabForwarding Revenue Charges`
		WHERE parenttype = 'Forwarding Job' AND parentfield = 'forwarding_revenue_charges'
		  AND IFNULL(is_invoiced, 0) = 0
		  AND parent IN (
		      SELECT name FROM `tabForwarding Job`
		      WHERE docstatus < 2 AND status NOT IN %(statuses)s
		  )
		""",
		{"statuses": NOT_ACTIVE_STATUSES},
	)[0][0]

	dnd_exposure = frappe.db.sql(
		"""
		SELECT COUNT(*), COALESCE(SUM(total_est_dnd_storage_cost), 0)
		FROM `tabForwarding Job`
		WHERE docstatus < 2 AND status NOT IN %(statuses)s AND IFNULL(total_est_dnd_storage_cost, 0) > 0
		""",
		{"statuses": NOT_ACTIVE_STATUSES},
	)[0]

	returnable_overdue = frappe.db.sql(
		"""
		SELECT COUNT(*) FROM `tabCargo Parcel Details` cpd
		INNER JOIN `tabForwarding Job` fj ON fj.name = cpd.parent
		WHERE cpd.parenttype = 'Forwarding Job' AND cpd.cargo_type = 'Containerised'
		  AND IFNULL(cpd.to_be_returned, 0) = 1 AND IFNULL(cpd.is_returned, 0) = 0
		  AND cpd.return_by_date IS NOT NULL AND cpd.return_by_date < %(today)s
		  AND fj.status NOT IN %(statuses)s
		""",
		{"today": today, "statuses": NOT_ACTIVE_STATUSES},
	)[0][0]

	jobs_by_status = frappe.db.sql(
		"""
		SELECT status, COUNT(*) AS count
		FROM `tabForwarding Job`
		WHERE docstatus < 2
		GROUP BY status
		ORDER BY FIELD(status, 'Draft', 'In Progress', 'Delivered', 'Completed', 'Closed', 'Cancelled')
		""",
		as_dict=True,
	)

	monthly_trend = _monthly_revenue_margin_trend(months=6)

	top_customers = frappe.db.sql(
		"""
		SELECT customer, COUNT(*) AS job_count
		FROM `tabForwarding Job`
		WHERE docstatus < 2 AND status NOT IN %(statuses)s
		GROUP BY customer
		ORDER BY job_count DESC
		LIMIT 5
		""",
		{"statuses": NOT_ACTIVE_STATUSES},
		as_dict=True,
	)

	top_corridors = frappe.db.sql(
		"""
		SELECT port_of_loading, port_of_discharge, COUNT(*) AS job_count
		FROM `tabForwarding Job`
		WHERE docstatus < 2 AND status NOT IN %(statuses)s
		  AND port_of_loading IS NOT NULL AND port_of_discharge IS NOT NULL
		GROUP BY port_of_loading, port_of_discharge
		ORDER BY job_count DESC
		LIMIT 5
		""",
		{"statuses": NOT_ACTIVE_STATUSES},
		as_dict=True,
	)

	blockers = frappe.get_all(
		"Forwarding Job",
		filters={
			"docstatus": ["<", 2],
			"status": ["not in", NOT_ACTIVE_STATUSES],
			"current_comment": ["is", "set"],
		},
		fields=["name", "customer", "status", "current_comment", "last_updated_on"],
		order_by="last_updated_on desc",
		limit_page_length=8,
	)

	return {
		"kpis": {
			"active_jobs": active_count,
			"overdue_arrivals": overdue_arrivals,
			"overdue_departures": overdue_departures,
			"missing_bl_docs": missing_bl,
			"uninvoiced_jobs": uninvoiced_jobs,
			"dnd_jobs": dnd_exposure[0] or 0,
			"dnd_exposure": flt(dnd_exposure[1] or 0, 2),
			"overdue_container_returns": returnable_overdue,
		},
		"jobs_by_status": jobs_by_status,
		"monthly_trend": monthly_trend,
		"top_customers": top_customers,
		"top_corridors": top_corridors,
		"recent_blockers": blockers,
	}


def _monthly_revenue_margin_trend(months=6):
	current = nowdate()
	buckets = []
	for i in range(months - 1, -1, -1):
		month_date = add_months(current, -i)
		buckets.append({
			"label": formatdate(get_first_day(month_date), "MMM YYYY"),
			"start": get_first_day(month_date),
			"end": get_last_day(month_date),
		})

	rows = frappe.db.sql(
		"""
		SELECT
			DATE_FORMAT(fj.revenue_recognised_on, '%%Y-%%m') AS month_key,
			COUNT(DISTINCT fj.name) AS shipment_count,
			SUM(COALESCE(si_agg.total_si, 0)) AS revenue,
			SUM(COALESCE(pi_agg.total_pi, 0)) AS cost
		FROM `tabForwarding Job` fj
		LEFT JOIN (
			SELECT forwarding_job_reference, SUM(base_grand_total) AS total_si
			FROM `tabSales Invoice`
			WHERE docstatus = 1 AND forwarding_job_reference IS NOT NULL
			GROUP BY forwarding_job_reference
		) si_agg ON si_agg.forwarding_job_reference = fj.name
		LEFT JOIN (
			SELECT forwarding_job_reference, SUM(base_grand_total) AS total_pi
			FROM `tabPurchase Invoice`
			WHERE docstatus = 1 AND forwarding_job_reference IS NOT NULL
			GROUP BY forwarding_job_reference
		) pi_agg ON pi_agg.forwarding_job_reference = fj.name
		WHERE fj.docstatus = 1 AND fj.revenue_recognised_on IS NOT NULL
		  AND fj.revenue_recognised_on BETWEEN %(start)s AND %(end)s
		GROUP BY month_key
		""",
		{"start": buckets[0]["start"], "end": buckets[-1]["end"]},
		as_dict=True,
	)
	by_month = {r.month_key: r for r in rows}

	trend = []
	for b in buckets:
		key = b["start"].strftime("%Y-%m") if hasattr(b["start"], "strftime") else str(b["start"])[:7]
		row = by_month.get(key)
		revenue = flt(row.revenue) if row else 0
		cost = flt(row.cost) if row else 0
		trend.append({
			"period": b["label"],
			"shipment_count": row.shipment_count if row else 0,
			"revenue": flt(revenue, 2),
			"cost": flt(cost, 2),
			"margin": flt(revenue - cost, 2),
		})
	return trend


# ============================================================
# SHIPMENTS (Forwarding Jobs)
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
			["consignee", "like", f"%{search}%"],
		]

	fields = [
		"name", "customer", "customer_reference", "direction", "shipment_mode",
		"status", "port_of_loading", "port_of_discharge", "destination",
		"vessel_flight_no", "bl_number", "cargo_count", "eta", "ata", "etd", "atd",
		"discharge_date", "current_comment", "last_updated_on",
	]

	jobs = frappe.get_list(
		"Forwarding Job",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
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

	return {"jobs": jobs, "total_count": total_count}


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
def get_job_detail(job_name):
	check_freightmas_role()
	check_doc_read_permission("Forwarding Job", job_name)

	doc = frappe.get_doc("Forwarding Job", job_name)

	header = {
		"name": doc.name,
		"customer": doc.customer,
		"customer_reference": doc.customer_reference,
		"shipper": doc.shipper,
		"consignee": doc.consignee,
		"notify_party": doc.notify_party,
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
		"is_bl_confirmed": doc.is_bl_confirmed,
		"currency": doc.currency,
		"incoterms": doc.incoterms,
		"current_comment": doc.current_comment,
		"last_updated_on": doc.last_updated_on,
		"last_updated_by": doc.last_updated_by,
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
		milestone_stages.append({
			"group": label,
			"milestones": [
				{
					"label": r.milestone_label,
					"is_completed": bool(r.is_completed),
					"completed_on": r.completed_on,
					"remarks": r.remarks,
				}
				for r in rows
			],
		})

	cargo = [
		{
			"name": r.name,
			"container_number": r.container_number or r.cargo_item_description,
			"container_type": r.container_type,
			"cargo_type": r.cargo_type,
			"to_be_returned": bool(r.to_be_returned),
			"return_by_date": r.return_by_date,
			"is_truck_required": bool(r.is_truck_required),
			"is_booked": bool(r.is_booked),
			"is_loaded": bool(r.is_loaded),
			"is_offloaded": bool(r.is_offloaded),
			"is_returned": bool(r.is_returned),
			"is_completed": bool(r.is_completed),
			"discharge_date": r.discharge_date,
			"gate_out_date": r.gate_out_date,
			"empty_return_date": r.empty_return_date,
			"api_container_status": r.api_container_status,
			"api_last_event": r.api_last_event,
			"api_last_event_date": r.api_last_event_date,
		}
		for r in (doc.cargo_parcel_details or [])
	]

	dnd_rows = [
		{
			"container_number": r.container_number,
			"container_type": r.container_type,
			"dnd_free_days": r.dnd_free_days,
			"dnd_rate_per_day": r.dnd_rate_per_day,
			"total_dnd_days": r.total_dnd_days,
			"chargeable_dnd_days": r.chargeable_dnd_days,
			"estimated_dnd_cost": r.estimated_dnd_cost,
			"storage_free_days": r.storage_free_days,
			"storage_rate_per_day": r.storage_rate_per_day,
			"total_storage_days": r.total_storage_days,
			"chargeable_storage_days": r.chargeable_storage_days,
			"estimated_storage_cost": r.estimated_storage_cost,
			"total_container_cost": r.total_container_cost,
		}
		for r in (doc.get("forwarding_dnd_storage_details") or [])
	]

	tracking = [
		{
			"event": r.event,
			"date": r.date,
			"source": r.source,
			"updated_by": r.updated_by,
		}
		for r in sorted(doc.get("tracking_timeline") or [], key=lambda r: r.idx or 0, reverse=True)
	][:15]

	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"forwarding_job_reference": doc.name, "docstatus": ["<", 2]},
		fields=["name", "customer", "posting_date", "due_date", "grand_total", "outstanding_amount", "status"],
	)
	purchase_invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"forwarding_job_reference": doc.name, "docstatus": ["<", 2]},
		fields=["name", "supplier", "posting_date", "due_date", "grand_total", "outstanding_amount", "status"],
	)

	finance = doc.get_job_totals_summary()

	return {
		"header": header,
		"shipment_dates": shipment_dates,
		"milestone_stages": milestone_stages,
		"cargo": cargo,
		"dnd_rows": dnd_rows,
		"dnd_totals": {
			"total_est_dnd_cost": doc.total_est_dnd_cost,
			"total_est_storage_cost": doc.total_est_storage_cost,
			"total_est_dnd_storage_cost": doc.total_est_dnd_storage_cost,
		},
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

	conditions = ["fj.docstatus = 1", "fj.status != 'Cancelled'"]
	values = {}
	if from_date:
		conditions.append("fj.creation >= %(from_date)s")
		values["from_date"] = from_date
	if to_date:
		conditions.append("fj.creation <= %(to_date)s")
		values["to_date"] = to_date
	if customer:
		conditions.append("fj.customer = %(customer)s")
		values["customer"] = customer

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			fj.name, fj.customer, fj.status,
			fj.total_quoted_revenue_base AS quoted_revenue,
			fj.total_quoted_cost_base AS quoted_cost,
			fj.total_quoted_profit_base AS quoted_profit,
			fj.total_working_revenue_base AS working_revenue,
			fj.total_working_cost AS working_cost,
			fj.total_working_profit_base AS working_profit,
			COALESCE(si.invoiced_revenue, 0) AS invoiced_revenue,
			COALESCE(pi.invoiced_cost, 0) AS invoiced_cost
		FROM `tabForwarding Job` fj
		LEFT JOIN (
			SELECT forwarding_job_reference, SUM(grand_total) AS invoiced_revenue
			FROM `tabSales Invoice`
			WHERE docstatus = 1 AND forwarding_job_reference IS NOT NULL
			GROUP BY forwarding_job_reference
		) si ON si.forwarding_job_reference = fj.name
		LEFT JOIN (
			SELECT forwarding_job_reference, SUM(grand_total) AS invoiced_cost
			FROM `tabPurchase Invoice`
			WHERE docstatus = 1 AND forwarding_job_reference IS NOT NULL
			GROUP BY forwarding_job_reference
		) pi ON pi.forwarding_job_reference = fj.name
		WHERE {where}
		ORDER BY fj.creation DESC
		LIMIT 200
		""",
		values,
		as_dict=True,
	)

	totals = {"quoted_revenue": 0, "quoted_cost": 0, "working_revenue": 0, "working_cost": 0,
			  "invoiced_revenue": 0, "invoiced_cost": 0}
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
		"""
		SELECT si.name, si.customer, si.posting_date, si.due_date, si.grand_total, si.outstanding_amount
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1 AND si.outstanding_amount > 0 AND si.forwarding_job_reference IS NOT NULL
		ORDER BY si.due_date ASC
		LIMIT 20
		""",
		as_dict=True,
	)

	outstanding_purchase = frappe.db.sql(
		"""
		SELECT pi.name, pi.supplier, pi.posting_date, pi.due_date, pi.grand_total, pi.outstanding_amount
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1 AND pi.outstanding_amount > 0 AND pi.forwarding_job_reference IS NOT NULL
		ORDER BY pi.due_date ASC
		LIMIT 20
		""",
		as_dict=True,
	)

	top_customers_by_revenue = frappe.db.sql(
		"""
		SELECT forwarding_job_reference AS job, customer,
		       SUM(grand_total) AS revenue
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND forwarding_job_reference IS NOT NULL
		GROUP BY customer
		ORDER BY revenue DESC
		LIMIT 5
		""",
		as_dict=True,
	)

	return {
		"jobs": rows,
		"totals": totals,
		"outstanding_sales_invoices": outstanding_sales,
		"outstanding_purchase_invoices": outstanding_purchase,
		"top_customers_by_revenue": top_customers_by_revenue,
		"monthly_trend": _monthly_revenue_margin_trend(months=12),
	}


# ============================================================
# DND & ADDITIONAL COSTS
# ============================================================

@frappe.whitelist()
def get_dnd_overview():
	check_freightmas_role()

	jobs = frappe.db.sql(
		"""
		SELECT
			fj.name, fj.customer, fj.status, fj.bl_number,
			fj.total_est_dnd_cost, fj.total_est_storage_cost, fj.total_est_dnd_storage_cost
		FROM `tabForwarding Job` fj
		WHERE fj.docstatus < 2 AND fj.status NOT IN %(statuses)s
		  AND IFNULL(fj.total_est_dnd_storage_cost, 0) > 0
		ORDER BY fj.total_est_dnd_storage_cost DESC
		""",
		{"statuses": NOT_ACTIVE_STATUSES},
		as_dict=True,
	)

	job_names = [j.name for j in jobs]
	containers = []
	if job_names:
		containers = frappe.db.sql(
			"""
			SELECT
				parent, container_number, container_type,
				dnd_free_days, dnd_rate_per_day, total_dnd_days, chargeable_dnd_days, estimated_dnd_cost,
				storage_free_days, storage_rate_per_day, total_storage_days, chargeable_storage_days, estimated_storage_cost,
				total_container_cost
			FROM `tabForwarding DND Storage Detail`
			WHERE parenttype = 'Forwarding Job' AND parent IN %(names)s
			ORDER BY total_container_cost DESC
			""",
			{"names": job_names},
			as_dict=True,
		)

	totals = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(total_est_dnd_cost), 0) AS total_dnd,
			COALESCE(SUM(total_est_storage_cost), 0) AS total_storage,
			COALESCE(SUM(total_est_dnd_storage_cost), 0) AS total_combined,
			COUNT(*) AS job_count
		FROM `tabForwarding Job`
		WHERE docstatus < 2 AND status NOT IN %(statuses)s AND IFNULL(total_est_dnd_storage_cost, 0) > 0
		""",
		{"statuses": NOT_ACTIVE_STATUSES},
		as_dict=True,
	)[0]

	overdue_returns = frappe.db.sql(
		"""
		SELECT cpd.parent AS job, cpd.container_number, cpd.return_by_date, fj.customer
		FROM `tabCargo Parcel Details` cpd
		INNER JOIN `tabForwarding Job` fj ON fj.name = cpd.parent
		WHERE cpd.parenttype = 'Forwarding Job' AND cpd.cargo_type = 'Containerised'
		  AND IFNULL(cpd.to_be_returned, 0) = 1 AND IFNULL(cpd.is_returned, 0) = 0
		  AND cpd.return_by_date IS NOT NULL AND cpd.return_by_date < %(today)s
		  AND fj.status NOT IN %(statuses)s
		ORDER BY cpd.return_by_date ASC
		""",
		{"today": nowdate(), "statuses": NOT_ACTIVE_STATUSES},
		as_dict=True,
	)

	return {
		"jobs": jobs,
		"containers": containers,
		"totals": totals,
		"overdue_returns": overdue_returns,
	}


# ============================================================
# EXCEL EXPORTS
# ============================================================

_HEADER_FILL = PatternFill("solid", fgColor="17406B")
_ZEBRA_FILL = PatternFill("solid", fgColor="F2F2F2")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_TITLE_FONT = Font(bold=True, size=14)
_SUBTITLE_FONT = Font(bold=True, size=11, color="667085")
_BORDER = Border(
	left=Side(style="thin", color="DDDDDD"),
	right=Side(style="thin", color="DDDDDD"),
	top=Side(style="thin", color="DDDDDD"),
	bottom=Side(style="thin", color="DDDDDD"),
)
_LEFT = Alignment(horizontal="left", vertical="center")
_RIGHT = Alignment(horizontal="right", vertical="center")
NUMERIC_TYPES = ("Currency", "Int", "Float", "Percent")


def _write_sheet(ws, sheet_title, columns, rows):
	"""columns: list of dicts {label, fieldname, fieldtype}."""
	ws.title = sheet_title[:31]
	ncols = len(columns)

	company = frappe.defaults.get_global_default("company") or frappe.defaults.get_user_default("Company") or "FreightMas"
	row_idx = 1
	ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=ncols)
	ws.cell(row=row_idx, column=1, value=company).font = _TITLE_FONT
	row_idx += 1

	ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=ncols)
	export_time = frappe.utils.now_datetime().strftime("%d-%b-%Y %H:%M")
	ws.cell(row=row_idx, column=1, value=f"{sheet_title} \u2014 Exported {export_time}").font = _SUBTITLE_FONT
	row_idx += 2

	header_row = row_idx
	for col_idx, col in enumerate(columns, start=1):
		cell = ws.cell(row=header_row, column=col_idx, value=col["label"])
		cell.font = _HEADER_FONT
		cell.fill = _HEADER_FILL
		cell.alignment = _LEFT
		cell.border = _BORDER
	row_idx += 1
	ws.freeze_panes = ws[f"A{header_row + 1}"]

	for i, row in enumerate(rows, start=1):
		fill = _ZEBRA_FILL if i % 2 == 0 else None
		for col_idx, col in enumerate(columns, start=1):
			value = row.get(col["fieldname"], "")
			cell = ws.cell(row=row_idx, column=col_idx)
			fieldtype = col.get("fieldtype", "Data")
			if fieldtype in NUMERIC_TYPES:
				cell.value = flt(value) if value not in (None, "") else 0
				cell.number_format = "0.0%" if fieldtype == "Percent" else "#,##0.00"
				cell.alignment = _RIGHT
			elif fieldtype in ("Date", "Datetime") and value:
				try:
					cell.value = formatdate(value, "dd-MMM-yy")
				except Exception:
					cell.value = str(value)
				cell.alignment = _LEFT
			else:
				cell.value = value if value not in (None,) else ""
				cell.alignment = _LEFT
			cell.border = _BORDER
			if fill:
				cell.fill = fill
		row_idx += 1

	for col_idx, col in enumerate(columns, start=1):
		max_length = len(col["label"])
		for row in ws.iter_rows(min_row=header_row, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
			for cell in row:
				try:
					max_length = max(max_length, len(str(cell.value)) if cell.value else 0)
				except Exception:
					pass
		ws.column_dimensions[get_column_letter(col_idx)].width = max(12, min(max_length + 2, 40))

	ws.sheet_view.showGridLines = False


def _send_workbook(wb, filename):
	output = BytesIO()
	wb.save(output)
	output.seek(0)
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = output.read()
	frappe.local.response.type = "binary"


def _timestamped(name):
	return f"{name}_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M')}.xlsx"


@frappe.whitelist()
def export_jobs(customer=None, status=None, direction=None, search=None):
	"""Export the (unpaginated, filtered) Shipments list to Excel."""
	check_freightmas_role()

	res = get_jobs(
		customer=customer, status=status, direction=direction, search=search,
		limit_start=0, limit_page_length=5000,
	)

	columns = [
		{"label": "Job", "fieldname": "name"},
		{"label": "Customer", "fieldname": "customer"},
		{"label": "Reference", "fieldname": "customer_reference"},
		{"label": "Direction", "fieldname": "direction"},
		{"label": "Mode", "fieldname": "shipment_mode"},
		{"label": "Origin", "fieldname": "port_of_loading"},
		{"label": "Discharge", "fieldname": "port_of_discharge"},
		{"label": "Destination", "fieldname": "destination"},
		{"label": "Vessel / Flight", "fieldname": "vessel_flight_no"},
		{"label": "BL Number", "fieldname": "bl_number"},
		{"label": "ETA", "fieldname": "eta", "fieldtype": "Date"},
		{"label": "ATA", "fieldname": "ata", "fieldtype": "Date"},
		{"label": "ETD", "fieldname": "etd", "fieldtype": "Date"},
		{"label": "ATD", "fieldname": "atd", "fieldtype": "Date"},
		{"label": "Status", "fieldname": "status"},
		{"label": "Milestone %", "fieldname": "milestone_percent", "fieldtype": "Float"},
	]

	wb = openpyxl.Workbook()
	_write_sheet(wb.active, "Shipments", columns, res["jobs"])
	_send_workbook(wb, _timestamped("Shipments"))


@frappe.whitelist()
def export_finance(from_date=None, to_date=None, customer=None):
	"""Export the Finance job profitability table to Excel."""
	check_freightmas_role()

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
	_write_sheet(wb.active, "Finance", columns, res["jobs"])
	_send_workbook(wb, _timestamped("Finance"))


@frappe.whitelist()
def export_dnd():
	"""Export the DND & Additional Costs overview (jobs + container detail) to Excel."""
	check_freightmas_role()

	res = get_dnd_overview()

	job_columns = [
		{"label": "Job", "fieldname": "name"},
		{"label": "Customer", "fieldname": "customer"},
		{"label": "Status", "fieldname": "status"},
		{"label": "BL Number", "fieldname": "bl_number"},
		{"label": "DND Cost", "fieldname": "total_est_dnd_cost", "fieldtype": "Currency"},
		{"label": "Storage Cost", "fieldname": "total_est_storage_cost", "fieldtype": "Currency"},
		{"label": "Total Exposure", "fieldname": "total_est_dnd_storage_cost", "fieldtype": "Currency"},
	]
	container_columns = [
		{"label": "Job", "fieldname": "parent"},
		{"label": "Container", "fieldname": "container_number"},
		{"label": "Type", "fieldname": "container_type"},
		{"label": "DND Free Days", "fieldname": "dnd_free_days", "fieldtype": "Int"},
		{"label": "DND Rate/Day", "fieldname": "dnd_rate_per_day", "fieldtype": "Currency"},
		{"label": "Chargeable DND Days", "fieldname": "chargeable_dnd_days", "fieldtype": "Int"},
		{"label": "DND Cost", "fieldname": "estimated_dnd_cost", "fieldtype": "Currency"},
		{"label": "Storage Free Days", "fieldname": "storage_free_days", "fieldtype": "Int"},
		{"label": "Storage Rate/Day", "fieldname": "storage_rate_per_day", "fieldtype": "Currency"},
		{"label": "Chargeable Storage Days", "fieldname": "chargeable_storage_days", "fieldtype": "Int"},
		{"label": "Storage Cost", "fieldname": "estimated_storage_cost", "fieldtype": "Currency"},
		{"label": "Total Cost", "fieldname": "total_container_cost", "fieldtype": "Currency"},
	]

	wb = openpyxl.Workbook()
	_write_sheet(wb.active, "DND Jobs", job_columns, res["jobs"])
	_write_sheet(wb.create_sheet("Containers"), "Containers", container_columns, res["containers"])
	_send_workbook(wb, _timestamped("DND_Additional_Costs"))
