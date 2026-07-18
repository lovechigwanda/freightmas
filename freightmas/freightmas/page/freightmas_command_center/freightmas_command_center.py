# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Whitelisted API for the FreightMas Command Center shell.

Home of cross-module concerns: branding and the executive overview that rolls
up every service line (Forwarding, Clearing, Border Clearing, Road Freight,
Trucking, Warehouse) plus the invoicing pipeline and cash position.

Per-module detail (shipment lists, job dossiers, module finance) stays in each
module's own dashboard controller; this file only produces the cheap,
aggregate-only rollup the landing page needs, and delegates branding + the
Forwarding overview to the original shipment_dashboard endpoints.
"""

import frappe
from frappe.utils import flt, nowdate

from freightmas.utils.permissions import check_freightmas_role
from freightmas.utils.dashboard_common import (
	NOT_ACTIVE,
	INVOICE_REF_FIELD,
	is_recognition_doctype,
)
from freightmas.freightmas.page.shipment_dashboard.shipment_dashboard import (
	get_branding as _forwarding_get_branding,
	get_overview as _forwarding_get_overview,
)


# Module registry: doctype -> (nav-route label, sidebar key). Order drives the
# scorecard grid on the executive page.
MODULE_ORDER = [
	("Forwarding Job", "Forwarding", "forwarding"),
	("Clearing Job", "Clearing", "clearing"),
	("Border Clearing Job", "Border Clearing", "border-clearing"),
	("Road Freight Job", "Road Freight", "road-freight"),
	("Trip", "Trucking", "trucking"),
	("Warehouse Job", "Warehouse", "warehouse"),
]

_CACHE_TTL = 300  # seconds - executive rollup tolerates 5-min staleness


# ============================================================
# BRANDING (delegated)
# ============================================================

@frappe.whitelist()
def get_branding():
	return _forwarding_get_branding()


@frappe.whitelist()
def get_overview():
	# Backwards-compatible: the Forwarding-only overview the SPA started with.
	return _forwarding_get_overview()


# ============================================================
# EXECUTIVE OVERVIEW (cross-module rollup)
# ============================================================

@frappe.whitelist()
def get_executive_overview(company=None):
	check_freightmas_role()

	# Cache keyed by company AND user - row-level permissions could otherwise
	# leak one user's aggregate to another.
	key = f"fm_exec_overview::{company or 'all'}::{frappe.session.user}"
	cached = frappe.cache().get_value(key)
	if cached is not None:
		return cached

	data = _build_executive_overview(company)
	frappe.cache().set_value(key, data, expires_in_sec=_CACHE_TTL)
	return data


def _company_clause(alias="", company=None):
	"""Return (' AND <alias>company = %(company)s', {'company': ...}) or ('', {})."""
	if not company:
		return "", {}
	col = f"{alias}company" if alias else "company"
	return f" AND {col} = %(company)s", {"company": company}


def _build_executive_overview(company=None):
	modules = [_module_scorecard(dt, label, key, company) for dt, label, key in MODULE_ORDER]

	totals = {
		"active": sum(m["active"] for m in modules),
		"revenue_invoiced": flt(sum(m["revenue_invoiced"] for m in modules), 2),
		"cost_invoiced": flt(sum(m["cost_invoiced"] for m in modules), 2),
		"attention": sum(m["attention"] for m in modules),
	}
	totals["margin_invoiced"] = flt(totals["revenue_invoiced"] - totals["cost_invoiced"], 2)
	totals["margin_pct"] = flt(
		totals["margin_invoiced"] / totals["revenue_invoiced"] * 100, 1
	) if totals["revenue_invoiced"] else 0

	return {
		"generated_on": frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M"),
		"company": company,
		"modules": modules,
		"totals": totals,
		"invoicing": _invoicing_pipeline_summary(company),
		"cash": _cash_position_summary(company),
		"trend": _combined_invoiced_trend(company, months=12),
		"top_customers": _top_customers_all_modules(company),
	}


# ------------------------------------------------------------
# Per-module scorecard
# ------------------------------------------------------------

def _module_scorecard(job_doctype, label, nav_key, company):
	cc, cvals = _company_clause(company=company)

	# Active count. Trip has no status field -> liveness is milestone-driven.
	if job_doctype == "Trip":
		active = frappe.db.sql(
			f"""SELECT COUNT(*) FROM `tabTrip`
			    WHERE docstatus < 2 AND IFNULL(is_completed, 0) = 0 {cc}""",
			cvals,
		)[0][0]
	else:
		statuses = tuple(NOT_ACTIVE[job_doctype])
		active = frappe.db.sql(
			f"""SELECT COUNT(*) FROM `tab{job_doctype}`
			    WHERE docstatus < 2 AND status NOT IN %(st)s {cc}""",
			{"st": statuses, **cvals},
		)[0][0]

	# Invoiced revenue / cost via the job reference field on the invoices.
	ref = INVOICE_REF_FIELD[job_doctype]
	inv_cc, inv_vals = _company_clause(company=company)
	revenue = frappe.db.sql(
		f"""SELECT COALESCE(SUM(base_grand_total), 0) FROM `tabSales Invoice`
		    WHERE docstatus = 1 AND {ref} IS NOT NULL {inv_cc}""",
		inv_vals,
	)[0][0]
	cost = frappe.db.sql(
		f"""SELECT COALESCE(SUM(base_grand_total), 0) FROM `tabPurchase Invoice`
		    WHERE docstatus = 1 AND {ref} IS NOT NULL {inv_cc}""",
		inv_vals,
	)[0][0]
	revenue, cost = flt(revenue), flt(cost)
	margin_pct = flt((revenue - cost) / revenue * 100, 1) if revenue else 0

	attention, attention_label = _module_attention(job_doctype, company)

	return {
		"doctype": job_doctype,
		"label": label,
		"nav_key": nav_key,
		"active": active,
		"revenue_invoiced": flt(revenue, 2),
		"cost_invoiced": flt(cost, 2),
		"margin_pct": margin_pct,
		"revenue_basis": "recognised" if is_recognition_doctype(job_doctype) else "invoiced",
		"attention": attention,
		"attention_label": attention_label,
	}


def _module_attention(job_doctype, company):
	"""A single, meaningful exception count + label per module. Defensive: any
	unexpected schema difference returns 0 rather than breaking the page."""
	today = nowdate()
	cc, cvals = _company_clause(company=company)
	try:
		if job_doctype == "Forwarding Job":
			n = frappe.db.sql(
				f"""SELECT COUNT(*) FROM `tabForwarding Job`
				    WHERE docstatus < 2 AND status NOT IN %(st)s {cc}
				      AND ((direction = 'Import' AND eta < %(today)s AND ata IS NULL)
				        OR (direction = 'Export' AND etd < %(today)s AND atd IS NULL))""",
				{"st": tuple(NOT_ACTIVE[job_doctype]), "today": today, **cvals},
			)[0][0]
			return n, "Overdue arrivals / departures"

		if job_doctype == "Clearing Job":
			n = frappe.db.sql(
				f"""SELECT COUNT(*) FROM `tabClearing Job`
				    WHERE docstatus < 2 AND status NOT IN %(st)s {cc}
				      AND IFNULL(is_discharged_from_port, 0) = 1
				      AND IFNULL(is_port_release_confirmed, 0) = 0""",
				{"st": tuple(NOT_ACTIVE[job_doctype]), **cvals},
			)[0][0]
			return n, "Discharged, awaiting port release"

		if job_doctype == "Border Clearing Job":
			n = frappe.db.sql(
				f"""SELECT COUNT(*) FROM `tabBorder Clearing Job`
				    WHERE docstatus < 2 AND status NOT IN %(st)s {cc}
				      AND IFNULL(is_duty_paid, 0) = 0""",
				{"st": tuple(NOT_ACTIVE[job_doctype]), **cvals},
			)[0][0]
			return n, "Duty not yet paid"

		if job_doctype == "Road Freight Job":
			n = frappe.db.sql(
				f"""SELECT COUNT(*) FROM `tabRoad Freight Job`
				    WHERE docstatus < 2 AND status NOT IN %(st)s {cc}
				      AND IFNULL(trucks_confirmed, 0) < IFNULL(no_of_trucks_required, 0)""",
				{"st": tuple(NOT_ACTIVE[job_doctype]), **cvals},
			)[0][0]
			return n, "Trucks not fully confirmed"

		if job_doctype == "Trip":
			n = frappe.db.sql(
				f"""SELECT COUNT(*) FROM `tabTrip`
				    WHERE docstatus < 2 AND IFNULL(is_completed, 0) = 0 {cc}
				      AND IFNULL(is_offloaded, 0) = 1 AND IFNULL(is_returned, 0) = 0""",
				cvals,
			)[0][0]
			return n, "Offloaded, empty not returned"

		if job_doctype == "Warehouse Job":
			n = frappe.db.sql(
				f"""SELECT COUNT(*) FROM `tabWarehouse Job`
				    WHERE docstatus < 2 AND status NOT IN %(st)s {cc}
				      AND IFNULL(pending_amount, 0) > 0""",
				{"st": tuple(NOT_ACTIVE[job_doctype]), **cvals},
			)[0][0]
			return n, "Storage accrued, unbilled"
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"exec_overview attention: {job_doctype}")
		return 0, ""
	return 0, ""


# ------------------------------------------------------------
# Invoicing pipeline (Invoice Register Entry)
# ------------------------------------------------------------

OPEN_INVOICE_STATUSES_EXCLUDED = ("Issued to Client", "Cancelled")


def _invoicing_pipeline_summary(company):
	cc, cvals = _company_clause(company=company)
	# Invoice Register Entry may or may not carry a company column; guard it.
	has_company = "company" in set(frappe.db.get_table_columns("Invoice Register Entry"))
	if not has_company:
		cc, cvals = "", {}

	by_status = frappe.db.sql(
		f"""SELECT status, COUNT(*) AS count, COALESCE(SUM(amount), 0) AS amount
		    FROM `tabInvoice Register Entry`
		    WHERE 1=1 {cc}
		    GROUP BY status ORDER BY count DESC""",
		cvals,
		as_dict=True,
	)

	open_count = sum(
		r.count for r in by_status if r.status not in OPEN_INVOICE_STATUSES_EXCLUDED
	)
	open_amount = flt(sum(
		r.amount for r in by_status if r.status not in OPEN_INVOICE_STATUSES_EXCLUDED
	), 2)

	overdue = frappe.db.sql(
		f"""SELECT COUNT(*) FROM `tabInvoice Register Entry`
		    WHERE IFNULL(is_overdue, 0) = 1 {cc}""",
		cvals,
	)[0][0]

	return {
		"open_count": open_count,
		"open_amount": open_amount,
		"overdue_count": overdue,
		"by_status": by_status,
	}


# ------------------------------------------------------------
# Cash position (Cash Reconciliation)
# ------------------------------------------------------------

def _cash_position_summary(company):
	cc, cvals = _company_clause(company=company)
	row = frappe.db.sql(
		f"""SELECT
		        COUNT(*) AS total,
		        SUM(CASE WHEN reconciliation_status = 'Balanced' THEN 1 ELSE 0 END) AS balanced,
		        SUM(CASE WHEN reconciliation_status <> 'Balanced' THEN 1 ELSE 0 END) AS with_difference,
		        COALESCE(SUM(difference), 0) AS total_difference
		    FROM `tabCash Reconciliation`
		    WHERE docstatus < 2 AND posting_date >= DATE_SUB(%(today)s, INTERVAL 30 DAY) {cc}""",
		{"today": nowdate(), **cvals},
		as_dict=True,
	)[0]
	return {
		"reconciliations_30d": row.total or 0,
		"balanced": int(row.balanced or 0),
		"with_difference": int(row.with_difference or 0),
		"total_difference": flt(row.total_difference or 0, 2),
	}


# ------------------------------------------------------------
# Combined invoiced trend (all modules, by invoice posting_date)
# ------------------------------------------------------------

def _combined_invoiced_trend(company, months=12):
	"""Total freight revenue/cost/margin per month across ALL modules, on an
	Invoiced basis (posting_date) - unambiguous where recognition doesn't apply
	to every module. An invoice counts once (it links to exactly one job type)."""
	ref_fields = list(INVOICE_REF_FIELD.values())
	any_ref = " OR ".join(f"{f} IS NOT NULL" for f in ref_fields)

	cc_si, vals = _company_clause(company=company)

	rev = frappe.db.sql(
		f"""SELECT DATE_FORMAT(posting_date, '%%Y-%%m') AS m,
		           COALESCE(SUM(base_grand_total), 0) AS revenue
		    FROM `tabSales Invoice`
		    WHERE docstatus = 1 AND ({any_ref})
		      AND posting_date >= DATE_SUB(%(today)s, INTERVAL %(months)s MONTH) {cc_si}
		    GROUP BY m""",
		{"today": nowdate(), "months": months, **vals},
		as_dict=True,
	)
	cost = frappe.db.sql(
		f"""SELECT DATE_FORMAT(posting_date, '%%Y-%%m') AS m,
		           COALESCE(SUM(base_grand_total), 0) AS cost
		    FROM `tabPurchase Invoice`
		    WHERE docstatus = 1 AND ({any_ref})
		      AND posting_date >= DATE_SUB(%(today)s, INTERVAL %(months)s MONTH) {cc_si}
		    GROUP BY m""",
		{"today": nowdate(), "months": months, **vals},
		as_dict=True,
	)

	rev_map = {r.m: flt(r.revenue) for r in rev}
	cost_map = {r.m: flt(r.cost) for r in cost}

	# Build an ordered month axis for the last `months` periods.
	from frappe.utils import add_months, get_first_day, formatdate
	series = []
	for i in range(months - 1, -1, -1):
		d = add_months(nowdate(), -i)
		key = get_first_day(d).strftime("%Y-%m")
		revenue = rev_map.get(key, 0)
		c = cost_map.get(key, 0)
		series.append({
			"period": formatdate(get_first_day(d), "MMM YY"),
			"revenue": flt(revenue, 2),
			"cost": flt(c, 2),
			"margin": flt(revenue - c, 2),
			"basis": "invoiced",
		})
	return series


# ------------------------------------------------------------
# Top customers across all modules (by invoiced revenue)
# ------------------------------------------------------------

def _top_customers_all_modules(company, limit=6):
	cc, vals = _company_clause(company=company)
	ref_fields = list(INVOICE_REF_FIELD.values())
	any_ref = " OR ".join(f"{f} IS NOT NULL" for f in ref_fields)
	rows = frappe.db.sql(
		f"""SELECT customer, COALESCE(SUM(base_grand_total), 0) AS revenue,
		           COUNT(*) AS invoices
		    FROM `tabSales Invoice`
		    WHERE docstatus = 1 AND ({any_ref}) {cc}
		    GROUP BY customer ORDER BY revenue DESC LIMIT %(limit)s""",
		{"limit": limit, **vals},
		as_dict=True,
	)
	for r in rows:
		r["revenue"] = flt(r.revenue, 2)
	return rows
