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
from frappe.utils import add_days, getdate, now_datetime, nowdate

from freightmas.freightmas.report.report_export_utils import send_excel_response
from freightmas.portal.security import (
	assert_customer_scope,
	check_portal_access,
	get_portal_customer_names,
	log_portal_access,
)
from freightmas.forwarding_service.utils.operational_phase import get_phase_label, resolve_operational_phase_filter
from freightmas.forwarding_service.utils.milestone_progress import forwarding_milestone_progress_map
from freightmas.forwarding_service.utils.client_tracking_view import (
	build_client_tracking_view,
	build_job_cargo_list,
	client_list_progress,
	resolve_client_milestone_report_mode,
)

NOT_ACTIVE_STATUSES = ["Completed", "Closed", "Cancelled"]

JOB_LIST_FIELDS = [
	"name", "customer_reference", "direction", "shipment_mode", "shipment_type",
	"status", "operational_phase", "operational_substage",
	"port_of_loading", "port_of_discharge", "destination",
	"vessel_flight_no", "bl_number", "cargo_count", "cargo_description", "eta", "ata", "etd", "atd",
	"discharge_date", "current_comment", "last_updated_on",
]

# ============================================================
# Tracking report exports (portal Excel + PDF)
# ============================================================

def _caller_customer_filter():
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			_("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)
	return customers


def _job_list_filters(
	customers,
	status=None,
	direction=None,
	operational_phase=None,
	operational_phases=None,
	overview_bucket=None,
	search=None,
):
	filters = {"docstatus": ["<", 2], "customer": ["in", customers]}
	if status:
		filters["status"] = status
	if direction:
		filters["direction"] = direction

	phase_filter = resolve_operational_phase_filter(
		operational_phase=operational_phase,
		operational_phases=operational_phases,
		overview_bucket=overview_bucket,
	)
	if phase_filter is not None:
		filters["operational_phase"] = phase_filter

	or_filters = None
	if search:
		or_filters = [
			["name", "like", f"%{search}%"],
			["customer_reference", "like", f"%{search}%"],
			["bl_number", "like", f"%{search}%"],
		]
	return filters, or_filters


def _count_jobs(filters, or_filters=None):
	if or_filters:
		return len(
			frappe.get_all(
				"Forwarding Job",
				filters=filters,
				or_filters=or_filters,
				pluck="name",
			)
		)
	return frappe.db.count("Forwarding Job", filters=filters)


def _delayed_job_clause():
	return """
		(
			(direction = 'Import' AND eta IS NOT NULL AND eta < %(today)s AND IFNULL(ata, '') = '')
			OR (direction = 'Export' AND etd IS NOT NULL AND etd < %(today)s AND IFNULL(atd, '') = '')
		)
	"""


def _portal_customer_display_name(customers):
	if len(customers) == 1:
		return frappe.db.get_value("Customer", customers[0], "customer_name") or customers[0]
	return _("Your Account")


def _fetch_tracking_report_jobs(customers, status=None, direction=None, operational_phase=None, operational_phases=None, overview_bucket=None, search=None):
	filters, or_filters = _job_list_filters(
		customers,
		status,
		direction,
		operational_phase,
		operational_phases,
		overview_bucket,
		search,
	)
	filters["docstatus"] = 0
	jobs = frappe.get_all(
		"Forwarding Job",
		filters=filters,
		or_filters=or_filters,
		fields=["name"],
		order_by="modified desc",
	)
	return jobs, filters, or_filters


def _portal_tracking_job_contexts(customers, status=None, direction=None, operational_phase=None, operational_phases=None, overview_bucket=None, search=None):
	from freightmas.forwarding_service.utils.client_tracking_export import build_job_contexts_from_docs

	jobs, _filters, _or_filters = _fetch_tracking_report_jobs(
		customers,
		status,
		direction,
		operational_phase,
		operational_phases,
		overview_bucket,
		search,
	)
	docs = [frappe.get_doc("Forwarding Job", job.name) for job in jobs]
	return build_job_contexts_from_docs(docs)


def _build_portal_tracking_pdf(customers, status=None, direction=None, operational_phase=None, operational_phases=None, overview_bucket=None, search=None):
	from freightmas.freightmas.page.shipment_dashboard.shipment_dashboard import _summarize_statuses
	from freightmas.utils.company_branding import company_logo_data_uri

	pdf_jobs = _portal_tracking_job_contexts(
		customers,
		status,
		direction,
		operational_phase,
		operational_phases,
		overview_bucket,
		search,
	)
	for i, ctx in enumerate(pdf_jobs, start=1):
		ctx["num"] = i

	company = frappe.db.get_single_value("Global Defaults", "default_company") or "FreightMas"
	company_name = frappe.db.get_value("Company", company, "company_name") or company
	customer_name = _portal_customer_display_name(customers)
	generated_on = now_datetime().strftime("%d %b %Y")

	html = frappe.render_template(
		"freightmas/templates/shipment_tracking_report.html",
		{
			"company": company_name,
			"customer": customer_name,
			"logo": company_logo_data_uri(company),
			"jobs": pdf_jobs,
			"generated_on": generated_on,
			"summary": _summarize_statuses(pdf_jobs),
		},
	)

	from frappe.utils.pdf import get_pdf

	return get_pdf(
		html,
		options={
			"orientation": "Portrait",
			"page-size": "A4",
			"margin-top": "12mm",
			"margin-bottom": "16mm",
			"margin-left": "10mm",
			"margin-right": "10mm",
			"footer-left": f"Prepared for {customer_name} — Confidential",
			"footer-right": "Page [page] of [topage]",
			"footer-font-size": "8",
			"footer-spacing": "4",
		},
	)


@frappe.whitelist()
def get_tracking_summary(
	status=None,
	direction=None,
	operational_phase=None,
	operational_phases=None,
	overview_bucket=None,
	search=None,
):
	check_portal_access()
	customers = _caller_customer_filter()
	today = getdate(nowdate())

	base_filters = {"docstatus": ["<", 2], "customer": ["in", customers]}
	active_filters = {**base_filters, "status": ["not in", NOT_ACTIVE_STATUSES]}
	at_port_filters = {
		**active_filters,
		"operational_phase": ["in", ["at_terminal", "under_port_clearance"]],
	}
	arriving_filters = {
		**active_filters,
		"direction": "Import",
		"eta": ["between", [today, add_days(today, 14)]],
		"ata": ["is", "not set"],
	}

	list_filters, or_filters = _job_list_filters(
		customers,
		status,
		direction,
		operational_phase,
		operational_phases,
		overview_bucket,
		search,
	)

	delayed_count = frappe.db.sql(
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

	log_portal_access("view_tracking_summary", doctype="Forwarding Job")

	return {
		"active_count": frappe.db.count("Forwarding Job", active_filters),
		"delayed_count": delayed_count,
		"at_port_count": frappe.db.count("Forwarding Job", at_port_filters),
		"arriving_soon_count": frappe.db.count("Forwarding Job", arriving_filters),
		"filtered_count": _count_jobs(list_filters, or_filters),
	}


@frappe.whitelist()
def get_jobs(
	status=None,
	direction=None,
	operational_phase=None,
	operational_phases=None,
	overview_bucket=None,
	search=None,
	limit_start=0,
	limit_page_length=20,
):
	check_portal_access()
	customers = _caller_customer_filter()

	filters, or_filters = _job_list_filters(
		customers,
		status,
		direction,
		operational_phase,
		operational_phases,
		overview_bucket,
		search,
	)

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

	total_count = _count_jobs(filters, or_filters)

	progress_map = forwarding_milestone_progress_map([j.name for j in jobs])
	today = getdate(nowdate())
	for j in jobs:
		j["milestone_percent"] = progress_map.get(j.name, 0)
		j["client_progress_percent"] = client_list_progress(j)
		j["operational_phase_label"] = get_phase_label(j.get("operational_phase"))
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
	report_mode = resolve_client_milestone_report_mode(doc.customer)
	milestone_percent = forwarding_milestone_progress_map([doc.name]).get(doc.name, 0)

	header = {
		"name": doc.name,
		"customer_reference": doc.customer_reference,
		"consignee": doc.consignee,
		"direction": doc.direction,
		"shipment_mode": doc.shipment_mode,
		"shipment_type": doc.shipment_type,
		"status": doc.status,
		"operational_phase": doc.operational_phase,
		"operational_phase_label": get_phase_label(doc.operational_phase),
		"milestone_percent": milestone_percent,
		"client_progress_percent": client_list_progress(doc),
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

	tracking_view = build_client_tracking_view(
		doc,
		milestone_report_mode=report_mode,
		milestone_percent=milestone_percent,
	)

	log_portal_access("view_shipment", doctype="Forwarding Job", docname=job_name, customer=customer)

	return {
		"header": header,
		"shipment_dates": shipment_dates,
		"milestone_report_mode": report_mode,
		"tracking_view": tracking_view,
		"cargo": build_job_cargo_list(doc),
	}


@frappe.whitelist()
def export_tracking_report(
	status=None,
	direction=None,
	operational_phase=None,
	operational_phases=None,
	overview_bucket=None,
	search=None,
):
	check_portal_access()
	customers = _caller_customer_filter()

	from freightmas.forwarding_service.utils.client_tracking_export import build_client_tracking_workbook

	job_contexts = _portal_tracking_job_contexts(
		customers,
		status,
		direction,
		operational_phase,
		operational_phases,
		overview_bucket,
		search,
	)
	customer_label = _portal_customer_display_name(customers)
	file_bytes = build_client_tracking_workbook(customer_label, job_contexts)
	filename = f"Tracking_Report_{now_datetime().strftime('%Y%m%d_%H%M')}.xlsx"
	send_excel_response(file_bytes, filename)

	log_portal_access("export_tracking_report", doctype="Forwarding Job")


@frappe.whitelist()
def export_tracking_report_pdf(
	status=None,
	direction=None,
	operational_phase=None,
	operational_phases=None,
	overview_bucket=None,
	search=None,
):
	check_portal_access()
	customers = _caller_customer_filter()

	pdf = _build_portal_tracking_pdf(
		customers,
		status,
		direction,
		operational_phase,
		operational_phases,
		overview_bucket,
		search,
	)

	filename = f"Shipment_Tracking_{now_datetime().strftime('%Y%m%d_%H%M')}.pdf"
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "download"

	log_portal_access("export_tracking_report_pdf", doctype="Forwarding Job")
