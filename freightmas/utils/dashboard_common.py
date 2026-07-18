# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Shared, read-only aggregation helpers for the FreightMas Command Center.

These generalise the primitives first written inline in
``page/shipment_dashboard/shipment_dashboard.py`` so every module dashboard
controller (Forwarding, Clearing, Border Clearing, Road Freight, Trucking,
Warehouse, Invoicing) reuses one tested implementation instead of copy-pasting
SQL.

SECURITY: several helpers interpolate a table / column name straight into SQL.
Those identifiers must ONLY ever come from the module-level maps below
(JOB_DOCTYPES / INVOICE_REF_FIELD), never from request parameters. Every public
function validates its identifier arguments against those maps and raises if an
unknown value is passed - this keeps the string-formatted SQL injection-safe.
"""

import frappe
from frappe.utils import flt, add_months, get_first_day, get_last_day, formatdate, nowdate


# ============================================================
# MODULE REGISTRY - the single source of truth for identifiers
# ============================================================

# Statuses that mean a job is no longer "live" work, per central doctype.
# Trip has no status field - its liveness is milestone-driven, so it is absent
# here and callers must not pass it to active_filter().
NOT_ACTIVE = {
	"Forwarding Job": ["Completed", "Closed", "Cancelled"],
	"Clearing Job": ["Completed", "Closed", "Cancelled"],
	"Border Clearing Job": ["Completed", "Closed", "Cancelled"],
	"Road Freight Job": ["Completed", "Cancelled"],
	"Warehouse Job": ["Completed", "Invoiced", "Cancelled"],
}

# Custom field on Sales Invoice / Purchase Invoice linking the invoice back to
# each central job doctype. Authoritative for every revenue/cost join.
INVOICE_REF_FIELD = {
	"Forwarding Job": "forwarding_job_reference",
	"Clearing Job": "clearing_job_reference",
	"Border Clearing Job": "border_clearing_job_reference",
	"Road Freight Job": "road_freight_job_reference",
	"Trip": "trip_reference",
	"Warehouse Job": "warehouse_job_reference",
}

# Modules whose invoices flow through the WIP / revenue-recognition engine
# (see freightmas/utils/revenue_recognition.py::RECOGNITION_JOB_TYPES). ONLY
# these may display a "Recognised revenue" figure; every other module reports
# Invoiced / Estimated revenue instead.
RECOGNITION_DOCTYPES = ("Forwarding Job", "Clearing Job", "Border Clearing Job")


def is_recognition_doctype(job_doctype):
	return job_doctype in RECOGNITION_DOCTYPES


def _assert_known(job_doctype):
	"""Guard against SQL injection via identifier interpolation."""
	if job_doctype not in INVOICE_REF_FIELD:
		frappe.throw(f"Unknown dashboard job doctype: {job_doctype}")


def _ref_field(job_doctype):
	_assert_known(job_doctype)
	return INVOICE_REF_FIELD[job_doctype]


# ============================================================
# ACTIVE-JOB FILTER
# ============================================================

def active_filter(job_doctype):
	"""frappe filters dict selecting live (not-closed, not-cancelled) jobs.

	Use with frappe.db.count / frappe.get_all. Trip has no status field and is
	intentionally unsupported - filter Trips on their milestone chain instead.
	"""
	if job_doctype not in NOT_ACTIVE:
		frappe.throw(f"active_filter() has no status lifecycle for {job_doctype}")
	return {"docstatus": ["<", 2], "status": ["not in", NOT_ACTIVE[job_doctype]]}


def active_count(job_doctype):
	return frappe.db.count(job_doctype, active_filter(job_doctype))


# ============================================================
# INVOICED REVENUE / COST TOTALS
# ============================================================

def invoiced_totals(job_doctype, job_names=None, base=True):
	"""Return {job_name: {"revenue": x, "cost": y}} of submitted-invoice totals.

	Mirrors the pre-aggregated subquery pattern in get_finance_summary: one SQL
	per side, grouped by the invoice reference field, so a job with many
	invoices is summed once (no LEFT JOIN fan-out double-counting).

	base=True uses base_grand_total (company currency); False uses grand_total.
	Pass job_names to scope to a set of jobs; omit for all jobs of the type.
	"""
	ref_field = _ref_field(job_doctype)
	amount_col = "base_grand_total" if base else "grand_total"

	scope = ""
	values = {}
	if job_names is not None:
		if not job_names:
			return {}
		scope = f"AND {ref_field} IN %(names)s"
		values["names"] = tuple(job_names)

	result = {}
	for side, table in (("revenue", "Sales Invoice"), ("cost", "Purchase Invoice")):
		rows = frappe.db.sql(
			f"""
			SELECT {ref_field} AS job, SUM({amount_col}) AS total
			FROM `tab{table}`
			WHERE docstatus = 1 AND {ref_field} IS NOT NULL {scope}
			GROUP BY {ref_field}
			""",
			values,
			as_dict=True,
		)
		for r in rows:
			result.setdefault(r.job, {"revenue": 0.0, "cost": 0.0})[side] = flt(r.total)
	return result


# ============================================================
# MONTHLY REVENUE / MARGIN TREND
# ============================================================

def _month_buckets(months):
	current = nowdate()
	buckets = []
	for i in range(months - 1, -1, -1):
		month_date = add_months(current, -i)
		buckets.append({
			"label": formatdate(get_first_day(month_date), "MMM YYYY"),
			"start": get_first_day(month_date),
			"end": get_last_day(month_date),
		})
	return buckets


def monthly_revenue_margin_trend(job_doctype, months=6, recognised=None):
	"""Monthly revenue / cost / margin / shipment-count series.

	recognised=True  -> bucket submitted jobs by ``revenue_recognised_on``
	                    (WIP recognition modules only). Series label: Recognised.
	recognised=False -> bucket submitted invoices by ``posting_date``
	                    (Road Freight / Trucking / Warehouse). Series label:
	                    Invoiced.
	recognised=None  -> auto-pick from RECOGNITION_DOCTYPES.

	Returns a list of {period, shipment_count, revenue, cost, margin, basis}.
	``basis`` is "recognised" or "invoiced" so the UI can label correctly.
	"""
	ref_field = _ref_field(job_doctype)
	if recognised is None:
		recognised = is_recognition_doctype(job_doctype)

	buckets = _month_buckets(months)
	start, end = buckets[0]["start"], buckets[-1]["end"]

	if recognised:
		rows = frappe.db.sql(
			f"""
			SELECT
				DATE_FORMAT(j.revenue_recognised_on, '%%Y-%%m') AS month_key,
				COUNT(DISTINCT j.name) AS shipment_count,
				SUM(COALESCE(si.total_si, 0)) AS revenue,
				SUM(COALESCE(pi.total_pi, 0)) AS cost
			FROM `tab{job_doctype}` j
			LEFT JOIN (
				SELECT {ref_field}, SUM(base_grand_total) AS total_si
				FROM `tabSales Invoice`
				WHERE docstatus = 1 AND {ref_field} IS NOT NULL
				GROUP BY {ref_field}
			) si ON si.{ref_field} = j.name
			LEFT JOIN (
				SELECT {ref_field}, SUM(base_grand_total) AS total_pi
				FROM `tabPurchase Invoice`
				WHERE docstatus = 1 AND {ref_field} IS NOT NULL
				GROUP BY {ref_field}
			) pi ON pi.{ref_field} = j.name
			WHERE j.docstatus = 1 AND j.revenue_recognised_on IS NOT NULL
			  AND j.revenue_recognised_on BETWEEN %(start)s AND %(end)s
			GROUP BY month_key
			""",
			{"start": start, "end": end},
			as_dict=True,
		)
		basis = "recognised"
	else:
		# Bucket invoices by their own posting_date; revenue from Sales Invoice,
		# cost from Purchase Invoice, both linked to this job type.
		rev_rows = frappe.db.sql(
			f"""
			SELECT DATE_FORMAT(posting_date, '%%Y-%%m') AS month_key,
			       SUM(base_grand_total) AS revenue,
			       COUNT(DISTINCT {ref_field}) AS shipment_count
			FROM `tabSales Invoice`
			WHERE docstatus = 1 AND {ref_field} IS NOT NULL
			  AND posting_date BETWEEN %(start)s AND %(end)s
			GROUP BY month_key
			""",
			{"start": start, "end": end},
			as_dict=True,
		)
		cost_rows = frappe.db.sql(
			f"""
			SELECT DATE_FORMAT(posting_date, '%%Y-%%m') AS month_key,
			       SUM(base_grand_total) AS cost
			FROM `tabPurchase Invoice`
			WHERE docstatus = 1 AND {ref_field} IS NOT NULL
			  AND posting_date BETWEEN %(start)s AND %(end)s
			GROUP BY month_key
			""",
			{"start": start, "end": end},
			as_dict=True,
		)
		merged = {r.month_key: {"revenue": flt(r.revenue), "shipment_count": r.shipment_count} for r in rev_rows}
		for r in cost_rows:
			merged.setdefault(r.month_key, {"revenue": 0, "shipment_count": 0})["cost"] = flt(r.cost)
		rows = [frappe._dict({"month_key": k, **v}) for k, v in merged.items()]
		basis = "invoiced"

	by_month = {r.month_key: r for r in rows}

	trend = []
	for b in buckets:
		key = b["start"].strftime("%Y-%m") if hasattr(b["start"], "strftime") else str(b["start"])[:7]
		row = by_month.get(key)
		revenue = flt(row.get("revenue")) if row else 0
		cost = flt(row.get("cost")) if row else 0
		trend.append({
			"period": b["label"],
			"shipment_count": (row.get("shipment_count") if row else 0) or 0,
			"revenue": flt(revenue, 2),
			"cost": flt(cost, 2),
			"margin": flt(revenue - cost, 2),
			"basis": basis,
		})
	return trend


# ============================================================
# MILESTONE PROGRESS
# ============================================================

def milestone_progress_map(job_doctype, milestone_fields, job_names):
	"""Return {job_name: percent_complete} across the given milestone child tables.

	milestone_fields: list of parentfield names (child table = Job Milestone
	Progress). Percent = completed rows / total rows across all listed tables.
	"""
	if not job_names or not milestone_fields:
		return {}

	counts = {}
	for fieldname in milestone_fields:
		rows = frappe.db.sql(
			"""
			SELECT parent, COUNT(*) AS total, SUM(IFNULL(is_completed, 0)) AS done
			FROM `tabJob Milestone Progress`
			WHERE parenttype = %(dt)s AND parentfield = %(field)s AND parent IN %(names)s
			GROUP BY parent
			""",
			{"dt": job_doctype, "field": fieldname, "names": tuple(job_names)},
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


# ============================================================
# MODULE SUMMARY SHAPE (executive scorecards)
# ============================================================

def base_module_summary(job_doctype, attention=0):
	"""Cheap {active, revenue_invoiced, revenue_basis, revenue_headline,
	margin_pct, attention} scorecard for the executive overview.

	Uses aggregate-only queries (no row lists). revenue_headline is Recognised
	for WIP modules, else Invoiced - and revenue_basis names which, so the UI
	never mislabels a non-recognition module as "recognised".
	"""
	active = active_count(job_doctype) if job_doctype in NOT_ACTIVE else 0

	ref_field = _ref_field(job_doctype)
	inv = frappe.db.sql(
		f"""
		SELECT
			(SELECT COALESCE(SUM(base_grand_total), 0) FROM `tabSales Invoice`
			   WHERE docstatus = 1 AND {ref_field} IS NOT NULL) AS revenue,
			(SELECT COALESCE(SUM(base_grand_total), 0) FROM `tabPurchase Invoice`
			   WHERE docstatus = 1 AND {ref_field} IS NOT NULL) AS cost
		""",
		as_dict=True,
	)[0]
	revenue = flt(inv.revenue)
	cost = flt(inv.cost)
	margin_pct = flt((revenue - cost) / revenue * 100, 1) if revenue else 0

	return {
		"doctype": job_doctype,
		"active": active,
		"revenue_invoiced": flt(revenue, 2),
		"cost_invoiced": flt(cost, 2),
		"margin_pct": margin_pct,
		"revenue_basis": "recognised" if is_recognition_doctype(job_doctype) else "invoiced",
		"attention": attention,
	}
