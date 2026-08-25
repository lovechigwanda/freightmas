# Client Portal dashboard overview - shipment + billing KPIs.

import os

import frappe
from frappe import _
from frappe.utils import add_days, get_year_start, getdate, nowdate

from freightmas.portal.api.invoices import INVOICE_LIST_FIELDS, _with_job_reference
from freightmas.portal.api.shipments import JOB_LIST_FIELDS, NOT_ACTIVE_STATUSES
from freightmas.portal.security import check_portal_access, get_portal_customer_names, log_portal_access
from freightmas.forwarding_service.utils.milestone_progress import forwarding_milestone_progress_map
from freightmas.forwarding_service.utils.operational_phase import (
	build_overview_phase_pipeline,
	get_phase_label,
)


def _job_is_overdue(job, today):
	return bool(
		(job.get("direction") == "Import" and job.get("eta") and getdate(job["eta"]) < today and not job.get("ata"))
		or (job.get("direction") == "Export" and job.get("etd") and getdate(job["etd"]) < today and not job.get("atd"))
	)


def _enrich_job_rows(jobs, today=None):
	today = today or getdate(nowdate())
	if not jobs:
		return jobs
	progress_map = forwarding_milestone_progress_map([j.name for j in jobs])
	for job in jobs:
		job["milestone_percent"] = progress_map.get(job.name, 0)
		job["operational_phase_label"] = get_phase_label(job.get("operational_phase"))
		job["is_overdue"] = _job_is_overdue(job, today)
	return jobs


def _billing_summary(customers, today):
	base_filters = {"docstatus": 1, "customer": ["in", customers]}
	outstanding_filters = {**base_filters, "outstanding_amount": [">", 0]}
	outstanding_amount = (
		frappe.get_all(
			"Sales Invoice",
			filters=outstanding_filters,
			fields=[{"SUM": "outstanding_amount", "as": "total"}],
		)[0].total
		or 0
	)
	overdue_amount = (
		frappe.get_all(
			"Sales Invoice",
			filters={**outstanding_filters, "due_date": ["<", today]},
			fields=[{"SUM": "outstanding_amount", "as": "total"}],
		)[0].total
		or 0
	)
	paid_ytd = (
		frappe.db.sql(
			"""
			SELECT SUM(per.allocated_amount) AS total
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			INNER JOIN `tabSales Invoice` si ON si.name = per.reference_name
			WHERE per.reference_doctype = 'Sales Invoice'
				AND si.customer IN %(customers)s
				AND pe.docstatus = 1
				AND pe.posting_date >= %(year_start)s
			""",
			{"customers": customers, "year_start": get_year_start(today)},
			as_dict=True,
		)[0].total
		or 0
	)
	return {
		"outstanding_amount": outstanding_amount,
		"overdue_amount": overdue_amount,
		"paid_ytd": paid_ytd,
	}


def _recent_tracking_updates(customers, limit=8):
	return frappe.db.sql(
		"""
		SELECT
			te.event,
			te.date,
			te.source,
			fj.name AS job_name,
			fj.customer_reference
		FROM `tabForwarding Tracking Event` te
		INNER JOIN `tabForwarding Job` fj ON fj.name = te.parent
		WHERE te.parenttype = 'Forwarding Job'
			AND fj.customer IN %(customers)s
			AND fj.docstatus < 2
			AND te.event IS NOT NULL AND te.event != ''
		ORDER BY te.date DESC, te.creation DESC
		LIMIT %(limit)s
		""",
		{"customers": customers, "limit": limit},
		as_dict=True,
	)


def _recent_client_documents(customers, limit=5):
	rows = frappe.db.sql(
		"""
		SELECT
			dc.name,
			dc.document,
			dc.date_submitted,
			dc.attach,
			fj.name AS job_name,
			fj.customer_reference
		FROM `tabForwarding Documents Checklist` dc
		INNER JOIN `tabForwarding Job` fj ON fj.name = dc.parent
		WHERE dc.parenttype = 'Forwarding Job'
			AND fj.customer IN %(customers)s
			AND fj.docstatus < 2
			AND dc.client_view = 1
			AND dc.attach IS NOT NULL AND dc.attach != ''
		ORDER BY COALESCE(dc.date_submitted, dc.modified) DESC
		LIMIT %(limit)s
		""",
		{"customers": customers, "limit": limit},
		as_dict=True,
	)
	for row in rows:
		row["file_name"] = os.path.basename(row.pop("attach") or "")
		row["document_label"] = row.get("document") or ""
	return rows


def _recent_invoices(customers, limit=5):
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "customer": ["in", customers]},
		fields=INVOICE_LIST_FIELDS,
		order_by="posting_date desc",
		limit_page_length=limit,
	)
	return [_with_job_reference(row) for row in invoices]


def _delayed_job_clause():
	return """
		(
			(direction = 'Import' AND eta IS NOT NULL AND eta < %(today)s AND IFNULL(ata, '') = '')
			OR (direction = 'Export' AND etd IS NOT NULL AND etd < %(today)s AND IFNULL(atd, '') = '')
		)
	"""


def _delayed_job_count(customers, today):
	return frappe.db.sql(
		f"""
		SELECT COUNT(*) AS total
		FROM `tabForwarding Job`
		WHERE customer IN %(customers)s
			AND docstatus < 2
			AND status NOT IN %(statuses)s
			AND {_delayed_job_clause()}
		""",
		{"customers": customers, "today": today, "statuses": NOT_ACTIVE_STATUSES},
	)[0][0]


def _delayed_jobs(customers, today, limit=5):
	names = frappe.db.sql(
		f"""
		SELECT name
		FROM `tabForwarding Job`
		WHERE customer IN %(customers)s
			AND docstatus < 2
			AND status NOT IN %(statuses)s
			AND {_delayed_job_clause()}
		ORDER BY COALESCE(eta, etd) ASC, modified DESC
		LIMIT %(limit)s
		""",
		{
			"customers": customers,
			"today": today,
			"statuses": NOT_ACTIVE_STATUSES,
			"limit": limit,
		},
		as_dict=True,
	)
	if not names:
		return []
	jobs = frappe.get_all(
		"Forwarding Job",
		filters={"name": ["in", [row.name for row in names]]},
		fields=JOB_LIST_FIELDS,
	)
	order = {row.name: idx for idx, row in enumerate(names)}
	jobs.sort(key=lambda job: order.get(job.name, 999))
	return _enrich_job_rows(jobs, today)


@frappe.whitelist()
def get_overview():
	check_portal_access()
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			_("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)

	today = getdate(nowdate())
	base_filters = {"docstatus": ["<", 2], "customer": ["in", customers]}
	active_filters = {**base_filters, "status": ["not in", NOT_ACTIVE_STATUSES]}

	phase_pipeline = build_overview_phase_pipeline(customers=customers)
	active_count = frappe.db.count("Forwarding Job", active_filters)

	recent_jobs = frappe.get_all(
		"Forwarding Job",
		filters=base_filters,
		fields=JOB_LIST_FIELDS,
		order_by="modified desc",
		limit_page_length=5,
	)
	_enrich_job_rows(recent_jobs, today)

	delayed_count = _delayed_job_count(customers, today)
	needs_attention = _delayed_jobs(customers, today)

	arriving_soon = frappe.get_all(
		"Forwarding Job",
		filters={
			**active_filters,
			"direction": "Import",
			"eta": ["between", [today, add_days(today, 14)]],
			"ata": ["is", "not set"],
		},
		fields=["name", "customer_reference", "port_of_loading", "destination", "port_of_discharge", "eta"],
		order_by="eta asc",
		limit_page_length=5,
	)

	billing = _billing_summary(customers, today)

	log_portal_access("view_dashboard", customer=customers[0] if len(customers) == 1 else None)

	return {
		"phase_pipeline": phase_pipeline,
		"active_count": active_count,
		"delayed_count": delayed_count,
		"recent_jobs": recent_jobs,
		"needs_attention": needs_attention,
		"arriving_soon": arriving_soon,
		"recent_updates": _recent_tracking_updates(customers),
		"recent_documents": _recent_client_documents(customers),
		"recent_invoices": _recent_invoices(customers),
		**billing,
	}
