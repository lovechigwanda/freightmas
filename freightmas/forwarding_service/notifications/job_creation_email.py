# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Job creation notification email — draft builder and send endpoint."""

import re

import frappe
from frappe import _
from frappe.utils import get_formatted_email

from freightmas.forwarding_service.notifications.job_creation_template_content import (
	JOB_CREATION_TEMPLATE_NAME,
)
from freightmas.notifications.email_templates import TEMPLATE_REGISTRY
from freightmas.utils.email_layout import (
	format_email_date,
	render_alert_box,
	render_detail_card,
	render_freightmas_email,
	render_sign_off,
)
from freightmas.utils.permissions import check_doc_read_permission

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

_SERVICE_MAP = [
	("requires_sea_air_freight", "Sea/Air Freight"),
	("requires_port_clearance", "Port Clearance"),
	("is_trucking_required", "Trucking Service"),
	("requires_border_clearance", "Border Clearance"),
	("requires_warehousing", "Warehousing"),
]


def get_missing_port_clearance_docs(job_doc) -> list[str]:
	"""Return incomplete Documentation-stage port clearance milestone labels."""
	if not job_doc.requires_port_clearance:
		return []
	missing = []
	for row in job_doc.port_clearance_milestones or []:
		if row.stage == "Documentation" and not row.is_completed:
			missing.append(row.milestone_label)
	return missing


def _notifications_enabled() -> bool:
	return bool(frappe.db.get_single_value(
		"FreightMas Settings", "enable_job_creation_notifications"
	))


def _default_template_name() -> str | None:
	return (
		frappe.db.get_single_value(
			"FreightMas Settings", "default_job_creation_email_template"
		)
		or JOB_CREATION_TEMPLATE_NAME
	)


def _validate_email_address(email):
	if not email or not _EMAIL_RE.match(email):
		frappe.throw(_("Enter a valid recipient email address."))


def _parse_cc_emails(cc_emails):
	if not cc_emails:
		return []
	parts = cc_emails.split(",") if isinstance(cc_emails, str) else list(cc_emails)
	parts = [e.strip() for e in parts if e and e.strip()]
	for email in parts:
		if not _EMAIL_RE.match(email):
			frappe.throw(_("Invalid CC email address: {0}").format(email))
	return parts


def _company_display_name(company_link):
	return frappe.db.get_value("Company", company_link, "company_name") or company_link


def _format_route(job_doc) -> str | None:
	legs = [job_doc.port_of_loading, job_doc.port_of_discharge, job_doc.destination]
	legs = [leg for leg in legs if leg]
	return " → ".join(legs) if legs else None


def _format_cargo_summary(job_doc) -> str | None:
	return job_doc.cargo_count or job_doc.cargo_description or None


def _consignee_name(job_doc) -> str | None:
	if not job_doc.consignee:
		return None
	return frappe.db.get_value("Customer", job_doc.consignee, "customer_name") or job_doc.consignee


def _format_services_enabled(job_doc) -> str | None:
	enabled = [label for field, label in _SERVICE_MAP if job_doc.get(field)]
	return ", ".join(enabled) if enabled else None


def _customer_display_name(job_doc) -> str:
	return frappe.db.get_value("Customer", job_doc.customer, "customer_name") or job_doc.customer


def _build_template_context(job_doc, customer_name=None, company_name=None) -> dict:
	missing_docs = get_missing_port_clearance_docs(job_doc)
	customer_name = customer_name or _customer_display_name(job_doc)
	company_name = company_name or _company_display_name(job_doc.company)

	context = job_doc.as_dict()
	context.update({
		"customer_name": customer_name,
		"company_name": company_name,
		"missing_docs": missing_docs,
		"route": _format_route(job_doc),
		"cargo_summary": _format_cargo_summary(job_doc),
		"consignee_name": _consignee_name(job_doc),
		"services_enabled": _format_services_enabled(job_doc),
		"eta_formatted": (
			frappe.format_value(job_doc.eta, {"fieldtype": "Date"}) if job_doc.eta else None
		),
		"bl_number_display": job_doc.bl_number or "—",
		"email_date": format_email_date(),
	})
	return context


def _build_shipment_detail_rows(job_doc) -> list[tuple[str, str]]:
	"""Return (label, value) pairs for the email details table."""
	rows = [
		("Job Reference", job_doc.name),
		("BL Number", job_doc.bl_number or "—"),
	]
	optional = [
		("Direction", job_doc.direction),
		("Mode", job_doc.shipment_mode),
		("Shipment Type", job_doc.shipment_type),
		("Route", _format_route(job_doc)),
		("ETA", frappe.format_value(job_doc.eta, {"fieldtype": "Date"}) if job_doc.eta else None),
		("Cargo", _format_cargo_summary(job_doc)),
		("Consignee", _consignee_name(job_doc)),
		("Services", _format_services_enabled(job_doc)),
	]
	for label, value in optional:
		if value:
			rows.append((label, value))
	return rows


def _email_type_for_template(template_name: str | None) -> str:
	if template_name and template_name in TEMPLATE_REGISTRY:
		return TEMPLATE_REGISTRY[template_name].get("email_type") or "SHIPMENT NOTIFICATION"
	return "SHIPMENT NOTIFICATION"


def _wrap_job_creation_message(body_html: str, job_doc, template_name: str | None = None) -> str:
	return render_freightmas_email(
		body_html,
		company=job_doc.company,
		email_type=_email_type_for_template(template_name),
		email_date=format_email_date(),
	)


def build_job_creation_subject(job_name, customer_name, customer_reference):
	return f"New Shipment - Job: {job_name} {customer_name} {customer_reference}"


def build_job_creation_message(job_doc, customer_name, company_name, missing_docs):
	"""Build the default HTML body for a job creation notification (Python fallback)."""
	from freightmas.utils.email_layout import render_headline

	safe_customer = frappe.utils.escape_html(customer_name or "")
	job_ref = frappe.utils.escape_html(job_doc.name)

	parts = [
		render_headline(f"Shipment registered — Job {job_doc.name}"),
		f'<p style="margin: 0 0 24px;">Dear {safe_customer},</p>',
		'<p style="margin: 0 0 24px;">Your shipment has been registered in our system. '
		"A summary of the key details is below.</p>",
		render_detail_card("Shipment Details", _build_shipment_detail_rows(job_doc)),
		f'<p style="margin: 0 0 24px;">Kindly quote the Job Reference <strong>{job_ref}</strong> '
		"in all future correspondence regarding this shipment.</p>",
	]

	if missing_docs:
		items = "".join(
			f'<li style="margin: 0 0 4px;">{frappe.utils.escape_html(label)}</li>'
			for label in missing_docs
		)
		callout_body = (
			"<p style=\"margin: 0 0 8px;\">The following documents are still needed to clear "
			f"this shipment through port:</p>"
			f'<ul style="margin: 0 0 8px; padding-left: 18px;">{items}</ul>'
			"<p style=\"margin: 0;\">Please send these at your earliest convenience to avoid "
			"delaying the shipment.</p>"
		)
		parts.append(render_alert_box("Action required — documents outstanding", callout_body))

	parts.extend([
		'<p style="margin: 0 0 24px;">If you have any questions, feel free to reach out — '
		"we're happy to help.</p>",
		render_sign_off(company_name),
	])
	return "".join(parts)


def render_job_creation_email(job_doc, template_name=None, customer_name=None, company_name=None):
	"""Render subject/message from Email Template, falling back to Python builder."""
	context = _build_template_context(job_doc, customer_name=customer_name, company_name=company_name)
	template_name = template_name or _default_template_name()

	if template_name and frappe.db.exists("Email Template", template_name):
		from frappe.email.doctype.email_template.email_template import get_email_template

		rendered = get_email_template(template_name, context)
		rendered["message"] = _wrap_job_creation_message(
			rendered["message"], job_doc, template_name=template_name
		)
		return rendered

	customer_name = context["customer_name"]
	company_name = context["company_name"]
	missing_docs = context["missing_docs"]
	body = build_job_creation_message(job_doc, customer_name, company_name, missing_docs)
	return {
		"subject": build_job_creation_subject(
			job_doc.name, customer_name, job_doc.customer_reference
		),
		"message": _wrap_job_creation_message(body, job_doc, template_name=template_name),
	}


@frappe.whitelist()
def get_job_creation_email_draft(forwarding_job):
	"""Return prefilled email draft for the job creation notification dialog."""
	check_doc_read_permission("Forwarding Job", forwarding_job)

	if not _notifications_enabled():
		return {"enabled": False}

	job = frappe.get_doc("Forwarding Job", forwarding_job)
	if job.job_creation_notification_sent:
		return {"enabled": False}

	customer_info = frappe.db.get_value(
		"Customer",
		job.customer,
		["customer_name", "tracking_email", "tracking_cc_emails", "tracking_email_enabled", "email_id"],
		as_dict=True,
	) or {}

	customer_name = customer_info.get("customer_name") or job.customer
	company_name = _company_display_name(job.company)
	missing_docs = get_missing_port_clearance_docs(job)
	default_template = _default_template_name()
	rendered = render_job_creation_email(
		job, template_name=default_template, customer_name=customer_name, company_name=company_name
	)

	return {
		"enabled": True,
		"to_email": customer_info.get("tracking_email") or customer_info.get("email_id") or "",
		"cc_emails": customer_info.get("tracking_cc_emails") or "",
		"subject": rendered["subject"],
		"message": rendered["message"],
		"missing_docs": missing_docs,
		"customer_name": customer_name,
		"job_name": job.name,
		"default_email_template": default_template if frappe.db.exists("Email Template", default_template or "") else None,
		"tracking_email_enabled": customer_info.get("tracking_email_enabled", 1),
	}


@frappe.whitelist()
def render_job_creation_email_template(forwarding_job, template_name):
	"""Re-render subject/message when the user picks a different Email Template."""
	check_doc_read_permission("Forwarding Job", forwarding_job)

	if not template_name:
		frappe.throw(_("Please select an email template."))

	job = frappe.get_doc("Forwarding Job", forwarding_job)
	return render_job_creation_email(job, template_name=template_name)


@frappe.whitelist()
def send_job_creation_notification(forwarding_job, to_email, subject, message, cc_emails=None):
	"""Send the job creation notification email and mark the job as notified."""
	check_doc_read_permission("Forwarding Job", forwarding_job)

	if not _notifications_enabled():
		frappe.throw(_("Job creation notifications are disabled in FreightMas Settings."))

	job = frappe.get_doc("Forwarding Job", forwarding_job)
	if job.job_creation_notification_sent:
		frappe.throw(_("Job creation notification has already been sent for this job."))

	_validate_email_address(to_email)
	cc = _parse_cc_emails(cc_emails)

	frappe.sendmail(
		recipients=[to_email],
		sender=get_formatted_email(frappe.session.user),
		cc=cc,
		subject=subject,
		message=message,
		reference_doctype="Forwarding Job",
		reference_name=job.name,
		delayed=False,
	)

	frappe.db.set_value(
		"Forwarding Job",
		job.name,
		"job_creation_notification_sent",
		1,
		update_modified=False,
	)

	return {
		"success": True,
		"message": _("Email sent successfully to {0}").format(to_email),
	}
