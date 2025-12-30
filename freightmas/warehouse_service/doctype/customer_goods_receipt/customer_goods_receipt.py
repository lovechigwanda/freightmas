# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today, now


class CustomerGoodsReceipt(Document):
	def validate(self):
		"""Validate Customer Goods Receipt"""
		self.validate_items()
		self.calculate_totals()
		self.calculate_item_volumes()
		self.set_item_numbers()
		self.set_quantity_remaining()
	
	def before_submit(self):
		"""Actions before submit"""
		self.validate_storage_locations()
		self.status = "Received"
	
	def on_submit(self):
		"""Actions on submit"""
		# CRITICAL: This does NOT create Stock Entry
		# Customer goods are tracked ONLY via custom doctypes
		self.create_goods_movement_records()
		self.update_bin_occupancy()
		self.create_or_link_warehouse_job()
		# Auto-create handling service log for receiving
		self.create_handling_log("OFFLOAD")
	
	def on_cancel(self):
		"""Actions on cancel"""
		self.cancel_goods_movements()
	
	def validate_items(self):
		"""Validate items table"""
		if not self.items:
			frappe.throw("Please add at least one item")
	
	def set_item_numbers(self):
		"""Set item numbers sequentially"""
		for idx, item in enumerate(self.items, start=1):
			item.item_number = idx
	
	def set_quantity_remaining(self):
		"""Initialize quantity remaining on new documents"""
		if self.is_new():
			for item in self.items:
				if not item.quantity_remaining:
					item.quantity_remaining = item.quantity
				item.status = "In Storage"
	
	def calculate_item_volumes(self):
		"""Calculate volume for each item"""
		for item in self.items:
			if item.length_cm and item.width_cm and item.height_cm:
				# Convert cm³ to m³
				item.volume_cbm = (item.length_cm * item.width_cm * item.height_cm) / 1000000
	
	def calculate_totals(self):
		"""Calculate total pallets, weight, and volume"""
		self.total_pallets = 0
		self.total_weight_kg = 0
		self.total_volume_cbm = 0
		
		for item in self.items:
			# Count storage units as pallets (simplified)
			self.total_pallets += flt(item.quantity)
			self.total_weight_kg += flt(item.weight_kg)
			self.total_volume_cbm += flt(item.volume_cbm)
	
	def validate_storage_locations(self):
		"""Ensure all items have storage locations assigned and have sufficient capacity"""
		for item in self.items:
			if not item.warehouse_bay:
				frappe.throw(f"Row {item.idx}: Please assign Warehouse Bay")
			if not item.warehouse_bin:
				frappe.throw(f"Row {item.idx}: Please assign Warehouse Bin")
			
			# Check bin capacity
			self.validate_bin_capacity(item)
	
	def validate_bin_capacity(self, item):
		"""Validate that bin has sufficient capacity for the item"""
		bin_doc = frappe.get_doc("Warehouse Bin", item.warehouse_bin)
		
		# Skip if no capacity limits set
		if not bin_doc.capacity_uom or not bin_doc.max_capacity:
			return
		
		# Check if bin can accommodate this item
		if not bin_doc.check_capacity_available(item.quantity, item.storage_unit_type):
			available = bin_doc.get_available_capacity()
			frappe.throw(
				f"Row {item.idx}: Bin {item.warehouse_bin} has insufficient capacity.<br>"
				f"Available: {available:.2f} {bin_doc.capacity_uom}<br>"
				f"Required: Capacity for {item.quantity} {item.storage_unit_type}",
				title="Capacity Exceeded"
			)
	
	def create_goods_movement_records(self):
		"""Create goods movement records for inbound receipt"""
		for item in self.items:
			movement = frappe.get_doc({
				"doctype": "Goods Movement",
				"movement_date": now(),
				"movement_type": "Inbound",
				"customer": self.customer,
				"goods_receipt": self.name,
				"destination_bay": item.warehouse_bay,
				"destination_bin": item.warehouse_bin,
				"moved_by": frappe.session.user,
				"reason": "New Receipt",
				"items": [{
					"goods_receipt_item": item.name,
					"storage_unit_type": item.storage_unit_type,
					"quantity_moved": item.quantity
				}]
			})
			movement.insert(ignore_permissions=True)
			movement.submit()
	
	def update_bin_occupancy(self):
		"""Update bin occupancy status and recalculate capacity"""
		for item in self.items:
			if item.warehouse_bin:
				bin_doc = frappe.get_doc("Warehouse Bin", item.warehouse_bin)
				# Trigger calculate_current_capacity via validate
				bin_doc.save(ignore_permissions=True)
	
	def cancel_goods_movements(self):
		"""Cancel associated goods movements"""
		movements = frappe.get_all("Goods Movement", {
			"goods_receipt": self.name,
			"docstatus": 1
		}, pluck="name")
		
		for movement in movements:
			doc = frappe.get_doc("Goods Movement", movement)
			doc.cancel()
	
	def create_or_link_warehouse_job(self):
		"""Create or link to warehouse job"""
		if not self.warehouse_job:
			# Check if there's an existing active job for this customer
			existing_job = frappe.db.get_value("Warehouse Job", {
				"customer": self.customer,
				"status": ["in", ["Draft", "Active"]],
				"job_type": ["in", ["Storage Only", "Storage + Handling"]]
			}, "name")
			
			if existing_job:
				self.warehouse_job = existing_job
				self.db_set("warehouse_job", existing_job, update_modified=False)
			else:
				# Create new warehouse job
				job = frappe.get_doc({
					"doctype": "Warehouse Job",
					"customer": self.customer,
					"job_date": self.receipt_date,
					"job_type": "Storage + Handling",
					"goods_receipt": self.name,
					"storage_start_date": self.receipt_date,
					"status": "Active"
				})
				job.insert(ignore_permissions=True)
				self.warehouse_job = job.name
				self.db_set("warehouse_job", job.name, update_modified=False)
	
	def create_handling_log(self, activity_code):
		"""Create handling service log for receipt/dispatch"""
		# Get the activity type
		activity = frappe.db.get_value("Handling Activity Type", 
			{"activity_code": activity_code, "is_active": 1}, 
			["name", "default_rate", "unit_of_measure"], as_dict=1)
		
		if not activity:
			return
		
		log = frappe.get_doc({
			"doctype": "Handling Service Log",
			"log_date": now(),
			"customer": self.customer,
			"warehouse_job": self.warehouse_job,
			"goods_receipt": self.name,
			"activity_type": activity.name,
			"performed_by": frappe.session.user,
			"items": [{
				"description": f"Offloading - {self.name}",
				"quantity": self.total_pallets,
				"uom": "Pallets",
				"rate": activity.default_rate,
				"amount": flt(self.total_pallets) * flt(activity.default_rate)
			}]
		})
		log.insert(ignore_permissions=True)
		log.submit()
	
	def update_status(self):
		"""Update status based on dispatch quantities"""
		if not self.items:
			return
		
		all_dispatched = all(flt(item.quantity_remaining) == 0 for item in self.items)
		any_dispatched = any(flt(item.quantity_remaining) < flt(item.quantity) for item in self.items)
		
		if all_dispatched:
			self.status = "Fully Dispatched"
		elif any_dispatched:
			self.status = "Partially Dispatched"
		else:
			self.status = "In Storage"
		
		self.db_set("status", self.status, update_modified=False)
