# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now


class CustomerGoodsDispatch(Document):
	def validate(self):
		"""Validate Customer Goods Dispatch"""
		self.validate_items()
		self.validate_quantities()
		self.calculate_totals()
	
	def before_submit(self):
		"""Actions before submit"""
		self.status = "Dispatched"
	
	def on_submit(self):
		"""Actions on submit"""
		# CRITICAL: This does NOT create Delivery Note or Stock Entry
		# Customer goods are tracked ONLY via custom doctypes
		self.update_receipt_quantities()
		self.create_goods_movement_records()
		self.update_receipt_status()
		# Auto-create handling service log for dispatch
		self.create_handling_log("LOAD")
	
	def on_cancel(self):
		"""Actions on cancel"""
		self.restore_receipt_quantities()
		self.cancel_goods_movements()
		self.update_receipt_status()
	
	def validate_items(self):
		"""Validate items table"""
		if not self.items:
			frappe.throw("Please add at least one item to dispatch")
		
		# Fetch customer from goods receipt
		if self.goods_receipt:
			receipt_customer = frappe.db.get_value("Customer Goods Receipt", self.goods_receipt, "customer")
			if receipt_customer != self.customer:
				frappe.throw(f"Customer mismatch. Receipt belongs to {receipt_customer}")
	
	def validate_quantities(self):
		"""Validate dispatch quantities against available quantities"""
		for item in self.items:
			if not item.goods_receipt_item:
				frappe.throw(f"Row {item.idx}: Please select Goods Receipt Item")
			
			# Get available quantity
			quantity_remaining = frappe.db.get_value(
				"Customer Goods Receipt Item", 
				item.goods_receipt_item, 
				"quantity_remaining"
			)
			
			if flt(item.quantity_to_dispatch) > flt(quantity_remaining):
				frappe.throw(
					f"Row {item.idx}: Dispatch quantity ({item.quantity_to_dispatch}) "
					f"exceeds available quantity ({quantity_remaining})"
				)
			
			if flt(item.quantity_to_dispatch) <= 0:
				frappe.throw(f"Row {item.idx}: Dispatch quantity must be greater than zero")
	
	def calculate_totals(self):
		"""Calculate total pallets and weight"""
		self.total_pallets_out = 0
		self.total_weight_kg = 0
		
		for item in self.items:
			self.total_pallets_out += flt(item.quantity_to_dispatch)
			
			# Get weight from receipt item
			weight_per_unit = frappe.db.get_value(
				"Customer Goods Receipt Item",
				item.goods_receipt_item,
				"weight_kg"
			) or 0
			self.total_weight_kg += flt(item.quantity_to_dispatch) * flt(weight_per_unit)
	
	def update_receipt_quantities(self):
		"""Update quantity_remaining in receipt items"""
		for item in self.items:
			receipt_item = frappe.get_doc("Customer Goods Receipt Item", item.goods_receipt_item)
			new_remaining = flt(receipt_item.quantity_remaining) - flt(item.quantity_to_dispatch)
			
			receipt_item.db_set("quantity_remaining", new_remaining, update_modified=False)
			
			# Update status
			if new_remaining <= 0:
				receipt_item.db_set("status", "Dispatched", update_modified=False)
	
	def restore_receipt_quantities(self):
		"""Restore quantity_remaining on cancel"""
		for item in self.items:
			receipt_item = frappe.get_doc("Customer Goods Receipt Item", item.goods_receipt_item)
			new_remaining = flt(receipt_item.quantity_remaining) + flt(item.quantity_to_dispatch)
			
			receipt_item.db_set("quantity_remaining", new_remaining, update_modified=False)
			receipt_item.db_set("status", "In Storage", update_modified=False)
	
	def create_goods_movement_records(self):
		"""Create goods movement records for outbound dispatch"""
		for item in self.items:
			movement = frappe.get_doc({
				"doctype": "Goods Movement",
				"movement_date": now(),
				"movement_type": "Outbound",
				"customer": self.customer,
				"goods_receipt": self.goods_receipt,
				"goods_dispatch": self.name,
				"source_bay": item.warehouse_bay,
				"source_bin": item.warehouse_bin,
				"moved_by": frappe.session.user,
				"reason": "Dispatch",
				"items": [{
					"goods_receipt_item": item.goods_receipt_item,
					"storage_unit_type": item.storage_unit_type,
					"quantity_moved": item.quantity_to_dispatch
				}]
			})
			movement.insert(ignore_permissions=True)
			movement.submit()
	
	def release_bin_occupancy(self):
		"""Release bins if fully emptied"""
		for item in self.items:
			# Check if this bin is now empty
			quantity_remaining = frappe.db.get_value(
				"Customer Goods Receipt Item",
				item.goods_receipt_item,
				"quantity_remaining"
			)
			
			if flt(quantity_remaining) <= 0:
				bin_doc = frappe.get_doc("Warehouse Bin", item.warehouse_bin)
				if bin_doc.current_goods_receipt == self.goods_receipt:
					bin_doc.mark_as_available()
	
	def restore_bin_occupancy(self):
		"""Restore bin occupancy on cancel"""
		for item in self.items:
			bin_doc = frappe.get_doc("Warehouse Bin", item.warehouse_bin)
			if not bin_doc.is_occupied:
				bin_doc.mark_as_occupied(
					customer=self.customer,
					goods_receipt=self.goods_receipt,
					occupied_date=frappe.db.get_value("Customer Goods Receipt", self.goods_receipt, "receipt_date")
				)
	
	def cancel_goods_movements(self):
		"""Cancel associated goods movements"""
		movements = frappe.get_all("Goods Movement", {
			"goods_dispatch": self.name,
			"docstatus": 1
		}, pluck="name")
		
		for movement in movements:
			doc = frappe.get_doc("Goods Movement", movement)
			doc.cancel()
	
	def update_receipt_status(self):
		"""Update the parent receipt's status"""
		if self.goods_receipt:
			receipt = frappe.get_doc("Customer Goods Receipt", self.goods_receipt)
			receipt.update_status()
	
	def create_handling_log(self, activity_code):
		"""Create handling service log for loading"""
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
			"goods_dispatch": self.name,
			"activity_type": activity.name,
			"performed_by": frappe.session.user,
			"items": [{
				"description": f"Loading - {self.name}",
				"quantity": self.total_pallets_out,
				"uom": "Pallets",
				"rate": activity.default_rate,
				"amount": flt(self.total_pallets_out) * flt(activity.default_rate)
			}]
		})
		log.insert(ignore_permissions=True)
		log.submit()
