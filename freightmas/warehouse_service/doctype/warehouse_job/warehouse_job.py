# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_datetime_str, date_diff, today, getdate


class WarehouseJob(Document):
	def validate(self):
		"""Validate Warehouse Job"""
		self.calculate_storage_days()
		self.calculate_storage_charges()
		self.calculate_handling_charges()
		self.calculate_totals()
		self.validate_invoiced_rows()
	
	def before_submit(self):
		"""Actions before submit"""
		if self.status == "Draft":
			self.status = "Active"
	
	def on_submit(self):
		"""Actions on submit"""
		pass
	
	def calculate_storage_days(self):
		"""Calculate total storage days"""
		if self.storage_start_date and self.storage_end_date:
			self.total_storage_days = date_diff(self.storage_end_date, self.storage_start_date) + 1
		elif self.storage_start_date:
			self.total_storage_days = date_diff(today(), self.storage_start_date) + 1
	
	def calculate_storage_charges(self):
		"""Calculate storage charge amounts"""
		for charge in self.storage_charges:
			# Calculate storage days
			if charge.start_date and charge.end_date:
				charge.storage_days = date_diff(charge.end_date, charge.start_date) + 1
			elif charge.start_date:
				charge.storage_days = date_diff(today(), charge.start_date) + 1
			else:
				charge.storage_days = 0
			
			# Calculate chargeable days
			charge.chargeable_days = max(0, charge.storage_days - flt(charge.free_days))
			
			# Calculate amount based on rate type
			if charge.rate_type == "Per Day":
				charge.amount = flt(charge.quantity) * flt(charge.rate_per_day) * charge.chargeable_days
			elif charge.rate_type == "Per Month":
				months = charge.chargeable_days / 30.0
				charge.amount = flt(charge.quantity) * flt(charge.rate_per_month) * months
			elif charge.rate_type == "Per SQM":
				# Assumes rate_per_day is actually rate per SQM per day
				charge.amount = flt(charge.quantity) * flt(charge.rate_per_day) * charge.chargeable_days
	
	def calculate_handling_charges(self):
		"""Calculate handling charge amounts"""
		for charge in self.handling_charges:
			charge.amount = flt(charge.quantity) * flt(charge.rate)
	
	def calculate_totals(self):
		"""Calculate total charges"""
		self.total_storage_charges = sum(flt(d.amount) for d in self.storage_charges)
		self.total_handling_charges = sum(flt(d.amount) for d in self.handling_charges)
		self.total_charges = self.total_storage_charges + self.total_handling_charges
		
		# Calculate invoiced and pending amounts
		self.invoiced_amount = sum(flt(d.amount) for d in self.storage_charges if d.is_invoiced)
		self.invoiced_amount += sum(flt(d.amount) for d in self.handling_charges if d.is_invoiced)
		self.pending_amount = self.total_charges - self.invoiced_amount
	
	def validate_invoiced_rows(self):
		"""Prevent editing invoiced rows"""
		if not self.is_new():
			old_doc = self.get_doc_before_save()
			if old_doc:
				# Check storage charges
				for idx, charge in enumerate(self.storage_charges):
					if idx < len(old_doc.storage_charges):
						old_charge = old_doc.storage_charges[idx]
						if old_charge.is_invoiced and (
							charge.quantity != old_charge.quantity or
							charge.rate_per_day != old_charge.rate_per_day or
							charge.rate_per_month != old_charge.rate_per_month
						):
							frappe.throw(f"Row {charge.idx} in Storage Charges is already invoiced and cannot be modified")
				
				# Check handling charges
				for idx, charge in enumerate(self.handling_charges):
					if idx < len(old_doc.handling_charges):
						old_charge = old_doc.handling_charges[idx]
						if old_charge.is_invoiced and (
							charge.quantity != old_charge.quantity or
							charge.rate != old_charge.rate
						):
							frappe.throw(f"Row {charge.idx} in Handling Charges is already invoiced and cannot be modified")
	
	@frappe.whitelist()
	def load_handling_logs(self):
		"""Load handling charges from Handling Service Logs"""
		# Get all handling logs for this job
		logs = frappe.get_all("Handling Service Log", {
			"warehouse_job": self.name,
			"docstatus": 1
		}, ["name"])
		
		for log_name in logs:
			log = frappe.get_doc("Handling Service Log", log_name["name"])
			
			# Check if already added
			existing = [d for d in self.handling_charges if d.get("handling_service_log") == log.name]
			if existing:
				continue
			
			# Get activity details
			activity = frappe.get_doc("Handling Activity Type", log.activity_type)
			
			for item in log.items:
				self.append("handling_charges", {
					"activity_date": getdate(log.log_date),
					"handling_activity_type": log.activity_type,
					"description": item.description,
					"quantity": item.quantity,
					"uom": item.uom,
					"rate": item.rate,
					"amount": item.amount
				})
		
		self.calculate_handling_charges()
		self.calculate_totals()
		frappe.msgprint("Handling charges loaded from service logs")
	
	@frappe.whitelist()
	def calculate_current_storage_charges(self):
		"""Auto-calculate storage charges from receipt items"""
		if not self.goods_receipt:
			frappe.throw("Please select a Goods Receipt")
		
		receipt = frappe.get_doc("Customer Goods Receipt", self.goods_receipt)
		
		# Get applicable rate card
		from freightmas.warehouse_service.doctype.storage_rate_card.storage_rate_card import StorageRateCard
		rate_card_name = StorageRateCard.get_applicable_rate_card(self.customer, self.storage_start_date)
		
		if not rate_card_name:
			frappe.msgprint("No applicable rate card found. Please enter rates manually.")
			return
		
		rate_card = frappe.get_doc("Storage Rate Card", rate_card_name)
		
		# Clear existing storage charges
		self.storage_charges = []
		
		for item in receipt.items:
			if flt(item.quantity_remaining) <= 0:
				continue
			
			# Find matching rate by storage unit type
			rate_item = None
			for rate in rate_card.rate_items:
				if rate.storage_unit_type == item.storage_unit_type:
					rate_item = rate
					break
			
			if not rate_item:
				continue
			
			self.append("storage_charges", {
				"goods_receipt_item": item.name,
				"storage_unit_type": item.storage_unit_type,
				"quantity": item.quantity_remaining,
				"start_date": self.storage_start_date or receipt.receipt_date,
				"end_date": self.storage_end_date,
				"rate_per_day": rate_item.rate_per_day,
				"rate_per_month": rate_item.rate_per_month,
				"rate_type": "Per Day" if rate_item.rate_per_day else "Per Month",
				"free_days": rate_item.free_days or 0
			})
		
		self.calculate_storage_charges()
		self.calculate_totals()
		frappe.msgprint(f"Storage charges calculated using rate card: {rate_card_name}")
	
	@frappe.whitelist()
	def create_sales_invoice(self, charges_to_invoice=None):
		"""Create Sales Invoice from selected charges"""
		if not charges_to_invoice:
			frappe.throw("Please select charges to invoice")
		
		import json
		if isinstance(charges_to_invoice, str):
			charges_to_invoice = json.loads(charges_to_invoice)
		
		# Create Sales Invoice
		si = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": self.customer,
			"posting_date": today(),
			"due_date": today(),
			"warehouse_job": self.name,
			"items": []
		})
		
		# Add storage charges
		for charge_name in charges_to_invoice.get("storage_charges", []):
			charge = frappe.get_doc("Warehouse Job Storage Charges", charge_name)
			if not charge.is_invoiced:
				si.append("items", {
					"item_code": "WMS-STORAGE",  # Create this service item
					"item_name": "Warehouse Storage Service",
					"description": f"Storage for {charge.quantity} {charge.storage_unit_type} ({charge.chargeable_days} days)",
					"qty": 1,
					"rate": charge.amount,
					"amount": charge.amount
				})
		
		# Add handling charges
		for charge_name in charges_to_invoice.get("handling_charges", []):
			charge = frappe.get_doc("Warehouse Job Handling Charges", charge_name)
			if not charge.is_invoiced:
				si.append("items", {
					"item_code": "WMS-HANDLING",  # Create this service item
					"item_name": "Warehouse Handling Service",
					"description": f"{charge.description} ({charge.quantity} {charge.uom})",
					"qty": 1,
					"rate": charge.amount,
					"amount": charge.amount
				})
		
		si.insert(ignore_permissions=True)
		
		# Mark charges as invoiced
		for charge_name in charges_to_invoice.get("storage_charges", []):
			frappe.db.set_value("Warehouse Job Storage Charges", charge_name, {
				"is_invoiced": 1,
				"sales_invoice": si.name
			})
		
		for charge_name in charges_to_invoice.get("handling_charges", []):
			frappe.db.set_value("Warehouse Job Handling Charges", charge_name, {
				"is_invoiced": 1,
				"sales_invoice": si.name
			})
		
		self.reload()
		self.calculate_totals()
		self.save()
		
		frappe.msgprint(f"Sales Invoice {si.name} created successfully")
		return si.name
