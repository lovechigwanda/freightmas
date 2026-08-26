# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""
Quotation Utilities

Handles:
1. Quotation workflow validation and email notifications
2. Job Order creation from accepted quotations
"""

import frappe
from frappe import _
from frappe.utils import today, getdate, get_fullname, flt, get_formatted_email, get_url

from freightmas.utils.email_layout import (
	render_detail_card,
	render_freightmas_email,
	render_headline,
	render_sign_off,
)


# ==============================
# WORKFLOW VALIDATION & EVENTS
# ==============================

def validate_quotation(doc, method=None):
	"""
	Validate quotation before save.

	Prevents accepting expired quotations.
	Ensures consistent precision for calculated financial fields.
	"""
	# Prevent accepting expired quotations
	if (doc.workflow_state == "Accepted" and
		doc.valid_till and
		getdate(doc.valid_till) < getdate(today())):
		frappe.throw(_("Cannot accept an expired quotation. Validity period has lapsed."))

	# Ensure precision consistency for calculated fields (2 decimal places)
	# This prevents floating-point drift causing "Cannot Update After Submit" errors
	if hasattr(doc, 'est_revenue'):
		doc.est_revenue = flt(doc.est_revenue, 2)
	if hasattr(doc, 'est_cost'):
		doc.est_cost = flt(doc.est_cost, 2)
	if hasattr(doc, 'est_profit'):
		doc.est_profit = flt(doc.est_profit, 2)


def on_quotation_workflow_change(doc, method=None):
	"""
	Triggered after quotation workflow state changes.
	
	Sends email notifications:
	- When submitted for approval → Sales Manager
	- When approved → Quotation Owner
	"""
	if not doc.workflow_state:
		return
	
	# Get the previous workflow state from the database
	prev_workflow_state = frappe.db.get_value("Quotation", doc.name, "workflow_state")
	
	# Only send email if state actually changed
	if prev_workflow_state == doc.workflow_state:
		return
	
	# Notification: Submitted for Approval → Sales Manager
	if doc.workflow_state == "Pending Approval" and prev_workflow_state == "Draft":
		send_approval_request_email(doc)
	
	# Notification: Approved → Quotation Owner
	elif doc.workflow_state == "Approved" and prev_workflow_state == "Pending Approval":
		send_approval_notification_email(doc)


def _quotation_detail_rows(doc, *, include_submitted_by=False):
	rows = [
		("Quotation", doc.name),
		("Customer", doc.party_name or doc.customer_name),
		("Amount", frappe.format_value(doc.grand_total, {"fieldtype": "Currency"}, doc)),
		("Valid Till", frappe.format_value(doc.valid_till, {"fieldtype": "Date"})),
	]
	if include_submitted_by:
		rows.append(("Submitted By", get_fullname(doc.owner)))
	return rows


def _build_quotation_workflow_body(doc, *, headline, salutation, intro, include_submitted_by=False, closing=None):
	company_name = frappe.db.get_value("Company", doc.company, "company_name") or doc.company
	quotation_url = get_url() + f"/app/quotation/{doc.name}"
	parts = [
		render_headline(headline),
		f'<p style="margin: 0 0 24px;">{salutation}</p>',
		f'<p style="margin: 0 0 24px;">{intro}</p>',
		render_detail_card("Quotation Details", _quotation_detail_rows(doc, include_submitted_by=include_submitted_by)),
	]
	if closing:
		parts.append(f'<p style="margin: 0 0 24px;">{closing}</p>')
	parts.append(
		f'<p style="margin: 0 0 24px;">Review quotation <strong>{frappe.utils.escape_html(doc.name)}</strong> '
		f'at {frappe.utils.escape_html(quotation_url)}</p>'
	)
	parts.append(render_sign_off(company_name))
	return "".join(parts)


def send_approval_request_email(doc):
	"""
	Send email to Sales Manager when quotation is submitted for approval.
	"""
	try:
		sales_managers = frappe.get_all(
			"Has Role",
			filters={"role": "Sales Manager", "parenttype": "User"},
			fields=["parent"],
			pluck="parent"
		)

		if not sales_managers:
			frappe.log_error(
				title="No Sales Manager found for quotation approval notification",
				message=f"Quotation {doc.name} submitted for approval but no Sales Manager role assigned"
			)
			return

		subject = f"Quotation {doc.name} - Approval Required"
		body = _build_quotation_workflow_body(
			doc,
			headline=f"Approval required — Quotation {doc.name}",
			salutation="Dear Sales Manager,",
			intro="A quotation has been submitted for your approval.",
			include_submitted_by=True,
		)
		message = render_freightmas_email(
			body,
			company=doc.company,
			email_type="INTERNAL NOTIFICATION",
		)

		for manager in sales_managers:
			frappe.sendmail(
				recipients=[manager],
				sender=get_formatted_email(frappe.session.user),
				subject=subject,
				message=message,
				reference_doctype="Quotation",
				reference_name=doc.name,
				delayed=False
			)

	except Exception:
		frappe.log_error(
			title=f"Failed to send approval request email for {doc.name}",
			message=frappe.get_traceback()
		)


def send_approval_notification_email(doc):
	"""
	Send email to quotation owner when quotation is approved.
	"""
	try:
		if not doc.owner:
			return

		subject = f"Quotation {doc.name} - Approved"
		body = _build_quotation_workflow_body(
			doc,
			headline=f"Quotation approved — {doc.name}",
			salutation=f"Dear {frappe.utils.escape_html(get_fullname(doc.owner))},",
			intro='Your quotation has been <strong style="color: #16a34a;">approved</strong> by the Sales Manager.',
			closing="You can now send this quotation to the customer.",
		)
		message = render_freightmas_email(
			body,
			company=doc.company,
			email_type="INTERNAL NOTIFICATION",
		)

		frappe.sendmail(
			recipients=[doc.owner],
			sender=get_formatted_email(frappe.session.user),
			subject=subject,
			message=message,
			reference_doctype="Quotation",
			reference_name=doc.name,
			delayed=False
		)

	except Exception:
		frappe.log_error(
			title=f"Failed to send approval notification email for {doc.name}",
			message=frappe.get_traceback()
		)


# ==============================
# JOB ORDER INTEGRATION
# ==============================

@frappe.whitelist()
def create_job_order_from_quotation(quotation_name):
	"""
	Create a Job Order from an Accepted Quotation.
	
	Args:
		quotation_name: Name of the Quotation document
	
	Returns:
		str: Name of the created Job Order
	"""
	# Get the quotation
	quotation = frappe.get_doc("Quotation", quotation_name)
	
	# Validate quotation state
	if hasattr(quotation, 'workflow_state'):
		if quotation.workflow_state != "Accepted":
			frappe.throw(
				_("Quotation must be in 'Accepted' state to create a Job Order. Current state: {0}")
				.format(quotation.workflow_state)
			)
	else:
		if quotation.docstatus != 1:
			frappe.throw(_("Quotation must be submitted to create a Job Order"))
	
	# Check for Forwarding job type
	if hasattr(quotation, 'job_type') and quotation.job_type != "Forwarding":
		frappe.throw(
			_("Job Orders can only be created for Forwarding quotations. This quotation is for {0}")
			.format(quotation.job_type)
		)
	
	# Check if quotation is for a Lead (not Customer)
	if quotation.quotation_to == "Lead":
		frappe.throw(
			_("Cannot create Job Order from a quotation to Lead.<br><br>Please convert the Lead <b>{0}</b> to a Customer first, then create a new Quotation for the Customer.")
			.format(quotation.party_name),
			title=_("Lead Not Converted")
		)
	
	# Ensure there's a valid customer
	if not quotation.party_name or quotation.quotation_to != "Customer":
		frappe.throw(_("This quotation must be linked to a Customer to create a Job Order"))
	
	# Check if job order already exists
	existing = frappe.db.get_value(
		"Job Order",
		{
			"quotation_reference": quotation_name,
			"docstatus": ["<", 2]
		},
		"name"
	)
	
	if existing:
		frappe.throw(
			_("A Job Order ({0}) already exists for this Quotation")
			.format(existing)
		)
	
	# Create new Job Order
	job_order = frappe.new_doc("Job Order")
	
	# Basic Information
	job_order.quotation_reference = quotation_name
	job_order.company = quotation.company
	job_order.customer = quotation.party_name
	job_order.order_date = frappe.utils.nowdate()
	job_order.prepared_by = frappe.session.user
	
	# Service Details
	job_order.service_type = "Forwarding"
	
	# Port mapping: origin_port → port_of_loading, port_of_discharge → port_of_discharge, destination_port → destination
	if hasattr(quotation, 'origin_port') and quotation.origin_port:
		job_order.port_of_loading = quotation.origin_port
	if hasattr(quotation, 'port_of_discharge') and quotation.port_of_discharge:
		job_order.port_of_discharge = quotation.port_of_discharge
	if hasattr(quotation, 'destination_port') and quotation.destination_port:
		job_order.destination = quotation.destination_port
	
	# Cargo Summary
	if hasattr(quotation, 'job_description'):
		job_order.job_description = quotation.job_description
	
	# Currency
	if hasattr(quotation, 'currency'):
		job_order.currency = quotation.currency
	
	# Copy items from quotation to job_order_charges
	if quotation.items:
		for item in quotation.items:
			charge_row = {
				"charge": item.item_code,
				"description": item.description or item.item_name,
				"qty": item.qty or 1,
				"sell_rate": item.rate or 0,
				"customer": quotation.party_name
			}
			
			# Copy cost fields if available
			if hasattr(item, 'buy_rate') and item.buy_rate:
				charge_row["buy_rate"] = item.buy_rate
			
			if hasattr(item, 'supplier') and item.supplier:
				charge_row["supplier"] = item.supplier
			
			job_order.append("job_order_charges", charge_row)
	
	# Save the job order
	job_order.insert()
	
	# Update quotation with Job Order reference and workflow state
	quotation_doc = frappe.get_doc("Quotation", quotation_name)
	quotation_doc.db_set("custom_job_order_reference", job_order.name)
	quotation_doc.db_set("workflow_state", "JO Created")
	
	frappe.msgprint(
		_("Job Order {0} created successfully").format(job_order.name),
		alert=True
	)
	
	return job_order.name
