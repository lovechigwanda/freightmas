# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, now


class JobOrder(Document):
	def validate(self):
		"""Validate job order before saving"""
		self.validate_quotation()
		self.validate_duplicate_job_order()
		self.fetch_items_from_quotation()
		self.calculate_totals()
	
	def validate_quotation(self):
		"""Ensure quotation exists and is in Accepted state"""
		if not self.quotation_reference:
			return
		
		quotation = frappe.get_doc("Quotation", self.quotation_reference)
		
		# Check if quotation has workflow_state field
		if hasattr(quotation, 'workflow_state'):
			if quotation.workflow_state != "Accepted":
				frappe.throw(
					_("Quotation {0} must be in 'Accepted' state to create a Job Order. Current state: {1}")
					.format(self.quotation_reference, quotation.workflow_state)
				)
		else:
			# Fallback: Check docstatus
			if quotation.docstatus != 1:
				frappe.throw(
					_("Quotation {0} must be submitted to create a Job Order")
					.format(self.quotation_reference)
				)
		
		# Ensure quotation is for Forwarding service
		if hasattr(quotation, 'job_type') and quotation.job_type != "Forwarding":
			frappe.throw(
				_("Job Order can only be created for Forwarding quotations. This quotation is for {0}")
				.format(quotation.job_type)
			)
	
	def validate_duplicate_job_order(self):
		"""Prevent creating multiple job orders from same quotation"""
		if self.is_new() and self.quotation_reference:
			existing = frappe.db.exists(
				"Job Order",
				{
					"quotation_reference": self.quotation_reference,
					"docstatus": ["<", 2],  # Not cancelled
					"name": ["!=", self.name]
				}
			)
			if existing:
				frappe.throw(
					_("A Job Order ({0}) already exists for Quotation {1}")
					.format(existing, self.quotation_reference)
				)
	
	def fetch_items_from_quotation(self):
		"""Copy items from quotation if not already populated"""
		if not self.quotation_reference:
			return
		
		# Only fetch if items table is empty
		if self.items:
			return
		
		quotation = frappe.get_doc("Quotation", self.quotation_reference)
		
		if not quotation.items:
			return
		
		# Copy each quotation item
		for item in quotation.items:
			self.append("items", {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"qty": item.qty,
				"uom": item.uom,
				"rate": item.rate,
				"amount": item.amount
			})
	
	def calculate_totals(self):
		"""Calculate total quoted amount from items"""
		total = 0.0
		for item in self.items:
			total += float(item.amount or 0)
		
		self.total_quoted_amount = total
	
	def before_submit(self):
		"""Actions before submitting"""
		# Set prepared_by if not already set
		if not self.prepared_by:
			self.prepared_by = frappe.session.user
		
		if not self.prepared_date:
			self.prepared_date = nowdate()
	
	def on_submit(self):
		"""Update quotation with link to this job order"""
		if self.quotation_reference:
			frappe.db.set_value(
				"Quotation",
				self.quotation_reference,
				"job_order_reference",
				self.name
			)
	
	def on_cancel(self):
		"""Remove link from quotation on cancel"""
		if self.quotation_reference:
			frappe.db.set_value(
				"Quotation",
				self.quotation_reference,
				"job_order_reference",
				None
			)
		
		# Prevent cancel if already converted to forwarding job
		if self.forwarding_job_reference:
			frappe.throw(
				_("Cannot cancel Job Order {0} as it has already been converted to Forwarding Job {1}")
				.format(self.name, self.forwarding_job_reference)
			)


@frappe.whitelist()
def create_forwarding_job(job_order_name):
	"""
	Create a Forwarding Job from a submitted Job Order.
	
	Args:
		job_order_name: Name of the Job Order document
	
	Returns:
		str: Name of the created Forwarding Job
	"""
	# Get the job order
	job_order = frappe.get_doc("Job Order", job_order_name)
	
	# Validate job order is submitted
	if job_order.docstatus != 1:
		frappe.throw(_("Job Order must be submitted before creating a Forwarding Job"))
	
	# Check if already converted
	if job_order.forwarding_job_reference:
		frappe.throw(
			_("This Job Order has already been converted to Forwarding Job {0}")
			.format(job_order.forwarding_job_reference)
		)
	
	# Create new Forwarding Job
	fwd_job = frappe.new_doc("Forwarding Job")
	
	# Basic Information
	fwd_job.company = job_order.company
	fwd_job.customer = job_order.customer
	fwd_job.customer_reference = job_order.customer_po_reference
	fwd_job.date_created = nowdate()
	fwd_job.created_by = frappe.session.user
	
	# Service Details
	fwd_job.direction = job_order.direction
	fwd_job.shipment_mode = job_order.shipment_mode
	fwd_job.incoterms = job_order.incoterms
	
	# Routing Information
	fwd_job.port_of_loading = job_order.origin_port
	fwd_job.destination = job_order.destination_port
	
	# Cargo Details
	fwd_job.cargo_description = job_order.cargo_description
	
	# Currency
	fwd_job.currency = job_order.currency
	
	# Operational flags
	fwd_job.is_trucking_required = job_order.is_trucking_required
	
	# Copy items to forwarding_costing_charges
	for item in job_order.items:
		fwd_job.append("forwarding_costing_charges", {
			"charge": item.item_code,
			"description": item.description,
			"qty": item.qty,
			"sell_rate": item.rate,
			"customer": job_order.customer
		})
	
	# Copy documents checklist
	for doc in job_order.documents_checklist:
		fwd_job.append("documents_checklist", {
			"document_name": doc.document_name,
			"is_received": doc.is_received,
			"received_date": doc.received_date,
			"notes": doc.notes
		})
	
	# Add notes about source
	fwd_job.special_instructions = (
		f"Created from Job Order: {job_order.name}\n"
		f"Quotation Reference: {job_order.quotation_reference}\n\n"
		f"{job_order.special_instructions or ''}"
	)
	
	# Save the forwarding job
	fwd_job.insert()
	
	# Update job order with forwarding job reference
	job_order.forwarding_job_reference = fwd_job.name
	job_order.job_created_date = now()
	job_order.job_created_by = frappe.session.user
	job_order.save()
	
	frappe.msgprint(
		_("Forwarding Job {0} created successfully").format(fwd_job.name),
		alert=True
	)
	
	return fwd_job.name
