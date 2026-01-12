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
	
	def after_insert(self):
		"""Actions after document is inserted"""
		# Auto-assign to operations user if specified
		if self.operations_assigned_to:
			self.assign_to_user(self.operations_assigned_to)
	
	def validate_quotation(self):
		"""Ensure quotation exists and is valid"""
		if not self.quotation_reference:
			return
		
		# Use db.get_value for efficient checking without loading full document
		if not frappe.db.exists("Quotation", self.quotation_reference):
			frappe.throw(_("Quotation {0} does not exist").format(self.quotation_reference))
	
	def validate_duplicate_job_order(self):
		"""Prevent creating multiple job orders from same quotation"""
		if self.is_new() and self.quotation_reference:
			existing = frappe.db.get_value(
				"Job Order",
				{
					"quotation_reference": self.quotation_reference,
					"docstatus": ["<", 2],
					"name": ["!=", self.name]
				},
				"name"
			)
			if existing:
				frappe.throw(
					_("A Job Order ({0}) already exists for Quotation {1}")
					.format(existing, self.quotation_reference)
				)
	
	def fetch_items_from_quotation(self):
		"""Copy items from quotation to job_order_charges if not already populated"""
		if not self.quotation_reference:
			return
		
		# Only fetch if job_order_charges table is empty
		if self.job_order_charges:
			return
		
		quotation = frappe.get_doc("Quotation", self.quotation_reference)
		
		if not quotation.items:
			return
		
		# Copy each quotation item to job_order_charges
		for item in quotation.items:
			charge_row = {
				"charge": item.item_code,
				"description": item.description or item.item_name,
				"qty": item.qty or 1,
				"sell_rate": item.rate or 0,
				"customer": self.customer
			}
			
			# If quotation item has cost fields, copy them too
			if hasattr(item, 'buy_rate') and item.buy_rate:
				charge_row["buy_rate"] = item.buy_rate
			
			if hasattr(item, 'supplier') and item.supplier:
				charge_row["supplier"] = item.supplier
			
			self.append("job_order_charges", charge_row)
	
	def calculate_totals(self):
		"""Calculate total quoted amount from job_order_charges"""
		total = 0.0
		
		# Calculate revenue_amount and cost_amount for each charge
		for charge in self.job_order_charges:
			# Calculate revenue amount
			charge.revenue_amount = float(charge.qty or 0) * float(charge.sell_rate or 0)
			# Calculate cost amount
			charge.cost_amount = float(charge.qty or 0) * float(charge.buy_rate or 0)
			# Add to total
			total += charge.revenue_amount
		
		self.total_quoted_amount = total
	
	def before_submit(self):
		"""Actions before submitting"""
		# Set prepared_by if not already set
		if not self.prepared_by:
			self.prepared_by = frappe.session.user
		
		# Validate all required fields for conversion are completed
		self.validate_for_conversion()
	
	def on_update(self):
		"""Handle assignment changes"""
		if self.has_value_changed("operations_assigned_to"):
			self.handle_assignment_change()
	
	def on_cancel(self):
		"""Prevent cancel if already converted to forwarding job"""
		if self.forwarding_job_reference:
			frappe.throw(
				_("Cannot cancel Job Order {0} as it has already been converted to Forwarding Job {1}")
				.format(self.name, self.forwarding_job_reference)
			)
	
	def assign_to_user(self, user):
		"""Assign this document to a user using Frappe's assignment system"""
		if not user:
			return
		
		# Check if already assigned to this user
		existing_assignments = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": self.doctype,
				"reference_name": self.name,
				"allocated_to": user,
				"status": "Open"
			}
		)
		
		if existing_assignments:
			return  # Already assigned
		
		# Use Frappe's assignment API
		try:
			from frappe.desk.form.assign_to import add
			add({
				"doctype": self.doctype,
				"name": self.name,
				"assign_to": [user],
				"description": f"Job Order for {self.customer} - Review and create Forwarding Job"
			})
		except Exception as e:
			frappe.log_error(f"Error assigning Job Order {self.name} to {user}: {str(e)}")
	
	def handle_assignment_change(self):
		"""Handle changes to operations_assigned_to field"""
		old_value = self.get_doc_before_save()
		old_user = old_value.operations_assigned_to if old_value else None
		new_user = self.operations_assigned_to
		
		# Remove old assignment if exists
		if old_user and old_user != new_user:
			self.remove_assignment(old_user)
		
		# Add new assignment
		if new_user:
			self.assign_to_user(new_user)
	
	def remove_assignment(self, user):
		"""Remove assignment from a user"""
		if not user:
			return
		
		try:
			from frappe.desk.form.assign_to import remove
			todos = frappe.get_all(
				"ToDo",
				filters={
					"reference_type": self.doctype,
					"reference_name": self.name,
					"allocated_to": user,
					"status": "Open"
				},
				pluck="name"
			)
			
			for todo in todos:
				remove(self.doctype, self.name, user)
				break  # Remove only once
		except Exception as e:
			frappe.log_error(f"Error removing assignment from {user} for Job Order {self.name}: {str(e)}")
	
	def validate_for_conversion(self):
		"""
		Validate that all required fields are filled before submission.
		This ensures Sales completes all information before handing over to Operations.
		"""
		missing_fields = []
		
		# Check required party information
		if not getattr(self, 'consignee', None):
			missing_fields.append("Consignee")
		
		# Check required service details
		if not getattr(self, 'shipment_type', None):
			missing_fields.append("Shipment Type")
		if not getattr(self, 'direction', None):
			missing_fields.append("Direction")
		if not getattr(self, 'shipment_mode', None):
			missing_fields.append("Shipment Mode")
		if not getattr(self, 'incoterms', None):
			missing_fields.append("Incoterms")
		
		# Check required routing information
		if not getattr(self, 'port_of_loading', None):
			missing_fields.append("Port of Origin")
		if not getattr(self, 'port_of_discharge', None):
			missing_fields.append("Port of Discharge")
		if not getattr(self, 'destination', None):
			missing_fields.append("Final Destination")
		
		# Check required dates
		if not getattr(self, 'eta', None):
			missing_fields.append("Estimated Arrival (ETA)")
		
		if missing_fields:
			frappe.throw(
				_("Cannot submit Job Order. Please complete the following required fields before handover to Operations:<br><br>• {0}")
				.format("<br>• ".join(missing_fields)),
				title=_("Incomplete Job Order")
			)


@frappe.whitelist()
def create_forwarding_job(job_order_name):
	"""
	Create a complete Forwarding Job from a submitted Job Order.
	
	Args:
		job_order_name: Name of the Job Order document
	
	Returns:
		str: Name of the created Forwarding Job
	"""
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
	fwd_job.customer_reference = job_order.customer_reference
	fwd_job.date_created = nowdate()
	fwd_job.created_by = frappe.session.user
	
	# Service Details
	fwd_job.direction = job_order.direction
	fwd_job.shipment_mode = job_order.shipment_mode
	fwd_job.shipment_type = job_order.shipment_type
	fwd_job.incoterms = job_order.incoterms
	
	# Party Information
	fwd_job.consignee = job_order.consignee
	
	# Routing Information
	fwd_job.port_of_loading = job_order.port_of_loading
	fwd_job.port_of_discharge = job_order.port_of_discharge
	fwd_job.destination = job_order.destination
	
	# Dates
	fwd_job.booking_date = job_order.booking_date or None
	fwd_job.etd = job_order.etd or None
	fwd_job.eta = job_order.eta
	
	# Currency
	fwd_job.currency = job_order.currency
	
	# Operational flags
	fwd_job.is_trucking_required = job_order.is_trucking_required
	
	# Copy job_order_charges to forwarding_costing_charges
	for charge in job_order.job_order_charges:
		costing_row = {
			"charge": charge.charge,
			"description": charge.description,
			"qty": charge.qty,
			"sell_rate": charge.sell_rate,
			"customer": charge.customer or job_order.customer
		}
		
		# Copy supplier and buy rate if available
		if charge.buy_rate:
			costing_row["buy_rate"] = charge.buy_rate
		
		if charge.supplier:
			costing_row["supplier"] = charge.supplier
		
		fwd_job.append("forwarding_costing_charges", costing_row)
	
	# Copy documents checklist
	for doc in job_order.documents_checklist:
		fwd_job.append("documents_checklist", {
			"document": doc.document,
			"attach": doc.attach,
			"is_submitted": doc.is_submitted,
			"date_submitted": doc.date_submitted,
			"is_verified": doc.is_verified,
			"date_verified": doc.date_verified
		})
	
	# Set Job Order reference in Forwarding Job
	fwd_job.job_order_reference = job_order.name
	
	# Save the forwarding job
	fwd_job.insert()
	
	# Update job order with forwarding job reference
	job_order.forwarding_job_reference = fwd_job.name
	job_order.job_created_date = now()
	job_order.job_created_by = frappe.session.user
	job_order.flags.ignore_permissions = True
	job_order.save()
	
	frappe.msgprint(
		_("Forwarding Job {0} created successfully").format(fwd_job.name),
		alert=True
	)
	
	return fwd_job.name

