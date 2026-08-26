# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Context builders for FreightMas email templates."""

from __future__ import annotations

import frappe

from freightmas.forwarding_service.notifications.job_creation_email import (
	_build_template_context as _job_creation_context,
	get_missing_port_clearance_docs,
)


def build_status_update_context(
	job_doc,
	*,
	status_label: str | None = None,
	status_datetime: str | None = None,
	current_location: str | None = None,
	container_list: str | None = None,
	next_step: str | None = None,
	customer_name: str | None = None,
	company_name: str | None = None,
) -> dict:
	"""Build Jinja context for the Shipment Status Update email template."""
	context = _job_creation_context(job_doc, customer_name=customer_name, company_name=company_name)
	context.update({
		"status_label": status_label,
		"status_datetime": status_datetime,
		"current_location": current_location,
		"container_list": container_list,
		"next_step": next_step,
	})
	return context


def build_documentation_request_context(job_doc, customer_name=None, company_name=None) -> dict:
	"""Build Jinja context for the Documentation Request email template."""
	context = _job_creation_context(job_doc, customer_name=customer_name, company_name=company_name)
	vessel_parts = [p for p in [job_doc.vessel_name, context.get("eta_formatted")] if p]
	context.update({
		"missing_docs": get_missing_port_clearance_docs(job_doc),
		"vessel_eta": " / ".join(vessel_parts) if vessel_parts else None,
		"free_time_ends": (
			frappe.format_value(job_doc.free_time_ends, {"fieldtype": "Date"})
			if job_doc.get("free_time_ends")
			else None
		),
	})
	return context


def build_invoice_email_context(invoice_name: str) -> dict:
	"""Build Jinja context for the Invoice Statement email template."""
	invoice = frappe.get_doc("Sales Invoice", invoice_name)
	customer_name = invoice.customer_name or invoice.customer
	company_name = frappe.db.get_value("Company", invoice.company, "company_name") or invoice.company

	job_reference = invoice.get("forwarding_job") or invoice.get("job_reference") or invoice.get("custom_job_reference")

	invoice_lines = []
	for item in invoice.items:
		invoice_lines.append({
			"description": item.item_name or item.description or item.item_code,
			"amount": frappe.format_value(item.amount, {"fieldtype": "Currency"}, invoice),
		})

	return {
		"invoice_name": invoice.name,
		"customer_name": customer_name,
		"company_name": company_name,
		"job_reference": job_reference,
		"invoice_date": frappe.format_value(invoice.posting_date, {"fieldtype": "Date"}),
		"payment_terms": invoice.payment_terms_template or invoice.payment_terms,
		"due_date": frappe.format_value(invoice.due_date, {"fieldtype": "Date"}) if invoice.due_date else None,
		"invoice_lines": invoice_lines,
		"currency": invoice.currency,
		"grand_total": frappe.format_value(invoice.grand_total, {"fieldtype": "Currency"}, invoice),
		"company": invoice.company,
	}


def render_template_by_name(template_name: str, context: dict, company: str | None = None) -> dict:
	"""Render an Email Template by name and wrap it in the FreightMas layout."""
	from frappe.email.doctype.email_template.email_template import get_email_template

	from freightmas.notifications.email_templates import TEMPLATE_REGISTRY
	from freightmas.utils.email_layout import format_email_date, render_freightmas_email

	if not frappe.db.exists("Email Template", template_name):
		frappe.throw(f"Email Template {template_name} not found")

	context = dict(context)
	context.setdefault("email_date", format_email_date())

	rendered = get_email_template(template_name, context)
	meta = TEMPLATE_REGISTRY.get(template_name, {})
	rendered["message"] = render_freightmas_email(
		rendered["message"],
		company=company or context.get("company"),
		email_type=meta.get("email_type"),
		email_date=context.get("email_date"),
	)
	return rendered
