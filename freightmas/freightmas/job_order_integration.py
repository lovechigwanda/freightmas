"""
Quotation Integration with Job Order

Adds custom field and button to create Job Order from Accepted Quotations
"""

import frappe
from frappe import _


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
	
	# Check if job order already exists
	existing = frappe.db.exists(
		"Job Order",
		{
			"quotation_reference": quotation_name,
			"docstatus": ["<", 2]  # Not cancelled
		}
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
	job_order.customer = quotation.customer_name
	job_order.order_date = frappe.utils.nowdate()
	
	# Service Details (will be fetched automatically via fetch_from)
	job_order.service_type = "Forwarding"
	
	# Cargo Summary
	if hasattr(quotation, 'cargo_description'):
		job_order.cargo_description = quotation.cargo_description
	
	# Currency
	if hasattr(quotation, 'currency'):
		job_order.currency = quotation.currency
	
	# Copy items from quotation
	if quotation.items:
		for item in quotation.items:
			job_order.append("items", {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"qty": item.qty,
				"uom": item.uom,
				"rate": item.rate,
				"amount": item.amount
			})
	
	# Save the job order
	job_order.insert()
	
	frappe.msgprint(
		_("Job Order {0} created successfully").format(job_order.name),
		alert=True
	)
	
	return job_order.name
