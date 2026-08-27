# Client Portal dashboard overview - shipment + billing KPIs.

import os

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, get_year_start, getdate, nowdate

from freightmas.portal.api.invoices import INVOICE_LIST_FIELDS, _with_job_reference
from freightmas.portal.api.shipments import JOB_LIST_FIELDS, NOT_ACTIVE_STATUSES
from freightmas.portal.security import check_portal_access, get_portal_customer_names, log_portal_access
from freightmas.forwarding_service.utils.milestone_progress import forwarding_milestone_progress_map
from freightmas.forwarding_service.utils.client_tracking_view import client_list_progress
from freightmas.forwarding_service.utils.operational_phase import (
	build_overview_phase_pipeline,
	get_phase_label,
)

ATTENTION_LIMIT = 7
IN_MOTION_LIMIT = 4


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
		job["client_progress_percent"] = client_list_progress(job)
		job["operational_phase_label"] = get_phase_label(job.get("operational_phase"))
		job["is_overdue"] = _job_is_overdue(job, today)
	return jobs


def _job_display_title(job):
	return job.get("customer_reference") or job.get("bl_number") or job.get("name")


def _job_cargo_subtitle(job):
	parts = []
	if job.get("cargo_count"):
		parts.append(job.cargo_count)
	if job.get("direction"):
		parts.append(job.direction)
	if job.get("shipment_type"):
		parts.append(job.shipment_type)
	return " · ".join(parts)


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
	overdue_filters = {**outstanding_filters, "due_date": ["<", today]}
	overdue_amount = (
		frappe.get_all(
			"Sales Invoice",
			filters=overdue_filters,
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
	overdue_invoice_count = frappe.db.count("Sales Invoice", overdue_filters)
	next_due_rows = frappe.get_all(
		"Sales Invoice",
		filters={**outstanding_filters, "due_date": [">=", today]},
		fields=INVOICE_LIST_FIELDS,
		order_by="due_date asc",
		limit_page_length=1,
	)
	next_due = _with_job_reference(next_due_rows[0]) if next_due_rows else None

	return {
		"outstanding_amount": outstanding_amount,
		"overdue_amount": overdue_amount,
		"paid_ytd": paid_ytd,
		"overdue_invoice_count": overdue_invoice_count,
		"next_due_invoice": next_due,
	}


def _recent_client_documents(customers, limit=3, since_days=14):
	cutoff = add_days(nowdate(), -since_days)
	rows = frappe.db.sql(
		"""
		SELECT
			dc.name,
			dc.document,
			dc.date_submitted,
			dc.attach,
			fj.name AS job_name,
			fj.customer_reference,
			fj.cargo_count
		FROM `tabForwarding Documents Checklist` dc
		INNER JOIN `tabForwarding Job` fj ON fj.name = dc.parent
		WHERE dc.parenttype = 'Forwarding Job'
			AND fj.customer IN %(customers)s
			AND fj.docstatus < 2
			AND dc.client_view = 1
			AND dc.attach IS NOT NULL AND dc.attach != ''
			AND COALESCE(dc.date_submitted, dc.modified) >= %(cutoff)s
		ORDER BY COALESCE(dc.date_submitted, dc.modified) DESC
		LIMIT %(limit)s
		""",
		{"customers": customers, "limit": limit, "cutoff": cutoff},
		as_dict=True,
	)
	for row in rows:
		row["file_name"] = os.path.basename(row.pop("attach") or "")
		row["document_label"] = row.get("document") or ""
	return rows


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


def _arriving_soon_jobs(customers, today, limit=5):
	jobs = frappe.get_all(
		"Forwarding Job",
		filters={
			"docstatus": ["<", 2],
			"customer": ["in", customers],
			"status": ["not in", NOT_ACTIVE_STATUSES],
			"direction": "Import",
			"eta": ["between", [today, add_days(today, 14)]],
			"ata": ["is", "not set"],
		},
		fields=JOB_LIST_FIELDS,
		order_by="eta asc",
		limit_page_length=limit,
	)
	return _enrich_job_rows(jobs, today)


def _arriving_soon_count(customers, today):
	return frappe.db.count(
		"Forwarding Job",
		{
			"docstatus": ["<", 2],
			"customer": ["in", customers],
			"status": ["not in", NOT_ACTIVE_STATUSES],
			"direction": "Import",
			"eta": ["between", [today, add_days(today, 14)]],
			"ata": ["is", "not set"],
		},
	)


def _overdue_invoices(customers, today, limit=3):
	rows = frappe.get_all(
		"Sales Invoice",
		filters={
			"docstatus": 1,
			"customer": ["in", customers],
			"outstanding_amount": [">", 0],
			"due_date": ["<", today],
		},
		fields=INVOICE_LIST_FIELDS,
		order_by="due_date asc",
		limit_page_length=limit,
	)
	return [_with_job_reference(row) for row in rows]


def _attention_items(customers, today):
	items = []
	seen_keys = set()

	def add_item(item):
		key = (item["type"], item.get("job_name"), item.get("invoice_name"), item.get("document_name"))
		if key in seen_keys:
			return
		seen_keys.add(key)
		items.append(item)

	for job in _delayed_jobs(customers, today, limit=ATTENTION_LIMIT):
		date_label = "ETA" if job.direction == "Import" else "ETD"
		date_value = job.eta if job.direction == "Import" else job.etd
		subtitle_parts = [_job_cargo_subtitle(job)] if _job_cargo_subtitle(job) != "" else []
		if date_value:
			subtitle_parts.append(f"{date_label} passed {formatdate(date_value, 'dd-MMM-yy')}")
		if job.current_comment:
			subtitle_parts.append(job.current_comment)
		add_item({
			"type": "delayed_shipment",
			"priority": 10,
			"title": _job_display_title(job),
			"subtitle": " · ".join(subtitle_parts) or job.name,
			"job_name": job.name,
			"invoice_name": None,
			"document_name": None,
			"document_job_name": None,
		})

	for invoice in _overdue_invoices(customers, today, limit=3):
		subtitle = f"Due {formatdate(invoice.due_date, 'dd-MMM-yy')} · Outstanding {invoice.outstanding_amount:,.2f}"
		if invoice.get("job_name"):
			subtitle += f" · {invoice.job_name}"
		add_item({
			"type": "overdue_invoice",
			"priority": 20,
			"title": invoice.name,
			"subtitle": subtitle,
			"job_name": invoice.get("job_name"),
			"invoice_name": invoice.name,
			"document_name": None,
			"document_job_name": None,
		})

	for job in _arriving_soon_jobs(customers, today, limit=3):
		if job.is_overdue:
			continue
		route = " → ".join(
			p for p in [job.port_of_loading, job.destination or job.port_of_discharge] if p
		)
		subtitle_parts = []
		if _job_cargo_subtitle(job):
			subtitle_parts.append(_job_cargo_subtitle(job))
		if job.eta:
			subtitle_parts.append(f"ETA {formatdate(job.eta, 'dd-MMM-yy')}")
		if route:
			subtitle_parts.append(route)
		add_item({
			"type": "arriving_soon",
			"priority": 30,
			"title": _job_display_title(job),
			"subtitle": " · ".join(subtitle_parts) or job.name,
			"job_name": job.name,
			"invoice_name": None,
			"document_name": None,
			"document_job_name": None,
		})

	for doc in _recent_client_documents(customers, limit=3):
		ref = doc.get("customer_reference") or doc.job_name
		subtitle = ref
		if doc.get("cargo_count"):
			subtitle = f"{ref} · {doc.cargo_count}"
		if doc.get("date_submitted"):
			subtitle += f" · {formatdate(doc.date_submitted, 'dd-MMM-yy')}"
		add_item({
			"type": "new_document",
			"priority": 40,
			"title": doc.document_label or doc.file_name or "Document",
			"subtitle": subtitle,
			"job_name": doc.job_name,
			"invoice_name": None,
			"document_name": doc.name,
			"document_job_name": doc.job_name,
		})

	items.sort(key=lambda row: (row["priority"], row.get("title") or ""))
	return items[:ATTENTION_LIMIT]


def _in_motion_jobs(customers, today, exclude_job_names=None):
	"""Recent active jobs excluding any already surfaced in the attention queue."""
	exclude = set(exclude_job_names or [])
	ordered_names = []

	active_filters = {
		"docstatus": ["<", 2],
		"customer": ["in", customers],
		"status": ["not in", NOT_ACTIVE_STATUSES],
	}
	extra = frappe.get_all(
		"Forwarding Job",
		filters=active_filters,
		fields=["name"],
		order_by="modified desc",
		limit_page_length=IN_MOTION_LIMIT * 4,
	)
	for row in extra:
		if row.name in exclude:
			continue
		if row.name not in ordered_names:
			ordered_names.append(row.name)
		if len(ordered_names) >= IN_MOTION_LIMIT:
			break

	if not ordered_names:
		return []

	jobs = frappe.get_all(
		"Forwarding Job",
		filters={"name": ["in", ordered_names]},
		fields=JOB_LIST_FIELDS,
	)
	order = {name: idx for idx, name in enumerate(ordered_names)}
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
	active_filters = {
		"docstatus": ["<", 2],
		"customer": ["in", customers],
		"status": ["not in", NOT_ACTIVE_STATUSES],
	}

	phase_pipeline = build_overview_phase_pipeline(customers=customers)
	active_count = frappe.db.count("Forwarding Job", active_filters)
	delayed_count = _delayed_job_count(customers, today)
	arriving_soon_count = _arriving_soon_count(customers, today)

	billing = _billing_summary(customers, today)
	attention_items = _attention_items(customers, today)
	attention_job_names = {
		item["job_name"] for item in attention_items if item.get("job_name")
	}

	log_portal_access("view_dashboard", customer=customers[0] if len(customers) == 1 else None)

	return {
		"phase_pipeline": phase_pipeline,
		"active_count": active_count,
		"delayed_count": delayed_count,
		"arriving_soon_count": arriving_soon_count,
		"attention_count": len(attention_items),
		"attention_items": attention_items,
		"in_motion_jobs": _in_motion_jobs(customers, today, exclude_job_names=attention_job_names),
		"financial_snapshot": billing,
		**billing,
	}
