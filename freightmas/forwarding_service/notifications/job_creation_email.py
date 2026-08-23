# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Job creation notification email — draft builder and send endpoint."""

import re

import frappe
from frappe import _
from frappe.utils import get_formatted_email

from freightmas.utils.permissions import check_doc_read_permission

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


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


def build_job_creation_message(job_doc, customer_name, company_name, missing_docs):
	"""Build the default HTML body for a job creation notification."""
	job_ref = frappe.utils.escape_html(job_doc.name)
	customer_ref = frappe.utils.escape_html(job_doc.customer_reference or "")
	safe_customer = frappe.utils.escape_html(customer_name or "")
	safe_company = frappe.utils.escape_html(company_name or "")

	parts = [
		f'<p style="margin: 0 0 1.25rem;">Dear {safe_customer},</p>',
		"<p>Your shipment has been registered in our system with the following details:</p>",
		'<table style="border-collapse: collapse; margin: 12px 0;">',
		f'<tr><td style="padding: 2px 24px 2px 0; font-weight: 600;">Job Reference:</td><td>{job_ref}</td></tr>',
		f'<tr><td style="padding: 2px 24px 2px 0; font-weight: 600;">Your Reference:</td><td>{customer_ref}</td></tr>',
		"</table>",
		f"<p>Please quote the Job Reference <strong>{job_ref}</strong> in all future correspondence regarding this shipment.</p>",
	]

	if missing_docs:
		items = "".join(
			f"<li>{frappe.utils.escape_html(label)}</li>" for label in missing_docs
		)
		parts.append(
			'<div style="background: #FAEEDA; border-radius: 8px; padding: 12px 16px; margin: 16px 0;">'
			'<p style="margin: 0 0 8px; font-weight: 600; color: #854F0B;">Action required — documents outstanding</p>'
			'<p style="margin: 0 0 8px; color: #2C2C2A;">The following documents are still needed to clear this shipment through port:</p>'
			f'<ul style="margin: 0 0 8px; padding-left: 20px; color: #2C2C2A;">{items}</ul>'
			'<p style="margin: 0; color: #2C2C2A;">Please send these at your earliest convenience to avoid delaying the shipment.</p>'
			"</div>"
		)

	parts.extend([
		"<p>If you have any questions, feel free to reach out — we're happy to help.</p>",
		'<p style="margin: 0 0 1.25rem;">Thank you for your business.</p>',
		f"<p>Best regards,<br>{safe_company}</p>",
	])
	return "".join(parts)


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

	return {
		"enabled": True,
		"to_email": customer_info.get("tracking_email") or customer_info.get("email_id") or "",
		"cc_emails": customer_info.get("tracking_cc_emails") or "",
		"subject": f"Shipment Registered - {job.name}",
		"message": build_job_creation_message(job, customer_name, company_name, missing_docs),
		"missing_docs": missing_docs,
		"customer_name": customer_name,
		"job_name": job.name,
		"tracking_email_enabled": customer_info.get("tracking_email_enabled", 1),
	}


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
