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
	job_order.customer = quotation.party_name  # This is the Customer name
	job_order.order_date = frappe.utils.nowdate()
	job_order.prepared_by = frappe.session.user  # Set the user who created it
	
	# Service Details (will be fetched automatically via fetch_from)
	job_order.service_type = "Forwarding"
	
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
				"customer": quotation.party_name  # Customer name from quotation
			}
			
			# Copy cost fields if available
			if hasattr(item, 'buy_rate') and item.buy_rate:
				charge_row["buy_rate"] = item.buy_rate
			
			if hasattr(item, 'supplier') and item.supplier:
				charge_row["supplier"] = item.supplier
			
			job_order.append("job_order_charges", charge_row)
	
	# Save the job order
	job_order.insert()
	
	frappe.msgprint(
		_("Job Order {0} created successfully").format(job_order.name),
		alert=True
	)
	
	return job_order.name
