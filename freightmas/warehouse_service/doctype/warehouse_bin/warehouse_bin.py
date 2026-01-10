# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class WarehouseBin(Document):
	def validate(self):
		"""Validate Warehouse Bin"""
		self.validate_bin_code()
		self.validate_against_bay_limits()
		self.calculate_current_capacity()
	
	def validate_bin_code(self):
		"""Ensure bin code is uppercase and clean"""
		if self.bin_code:
			self.bin_code = self.bin_code.strip().upper()
	
	def validate_against_bay_limits(self):
		"""Validate bin capacity doesn't exceed bay limits"""
		if not self.bay:
			return
		
		bay = frappe.get_doc("Warehouse Bay", self.bay)
		
		# Check pallet capacity
		if self.uom == "Pallets" and self.max_capacity and bay.max_pallets:
			# Get total pallet capacity of other bins in this bay
			total_pallets = frappe.db.sql("""
				SELECT SUM(max_capacity) as total
				FROM `tabWarehouse Bin`
				WHERE bay = %s
				AND uom = 'Pallets'
				AND name != %s
			""", (self.bay, self.name or ""))
			
			current_total = flt(total_pallets[0][0] if total_pallets and total_pallets[0][0] else 0, 2)
			new_total = current_total + flt(self.max_capacity, 2)
			
			if new_total > bay.max_pallets:
				frappe.throw(
					f"Total pallet capacity ({new_total}) would exceed bay limit ({bay.max_pallets}). "
					f"Current bins use {current_total} pallets.",
					title="Bay Capacity Exceeded"
				)
		
		# Check SQM capacity
		if self.uom == "SQM" and self.max_capacity and bay.capacity_sqm:
			total_sqm = frappe.db.sql("""
				SELECT SUM(max_capacity)
				FROM `tabWarehouse Bin`
				WHERE bay = %s
				AND uom = 'SQM'
				AND name != %s
			""", (self.bay, self.name or ""))
			
			current_total = flt(total_sqm[0][0] if total_sqm and total_sqm[0][0] else 0, 2)
			new_total = current_total + flt(self.max_capacity, 2)
			
			if new_total > bay.capacity_sqm:
				frappe.throw(
					f"Total SQM capacity ({new_total}) would exceed bay limit ({bay.capacity_sqm}). "
					f"Current bins use {current_total} SQM.",
					title="Bay Area Exceeded"
				)
		
		# Check weight capacity
		if self.max_weight_kg and bay.max_weight_kg:
			total_weight = frappe.db.sql("""
				SELECT SUM(max_weight_kg) as total
				FROM `tabWarehouse Bin`
				WHERE bay = %s
				AND name != %s
			""", (self.bay, self.name or ""))
			
			current_total = flt(total_weight[0][0] if total_weight and total_weight[0][0] else 0, 2)
			new_total = current_total + flt(self.max_weight_kg, 2)
			
			if new_total > bay.max_weight_kg:
				frappe.throw(
					f"Total weight capacity ({new_total} kg) would exceed bay limit ({bay.max_weight_kg} kg). "
					f"Current bins use {current_total} kg.",
					title="Bay Weight Limit Exceeded"
				)
	
	def calculate_current_capacity(self):
		"""Calculate current capacity used based on allocations"""
		if not self.uom or not self.max_capacity:
			return
		
		capacity_used = self.get_current_capacity_used()
		self.current_capacity_used = capacity_used
		
		if self.max_capacity > 0:
			self.capacity_utilization_pct = (capacity_used / self.max_capacity) * 100
		else:
			self.capacity_utilization_pct = 0
	
	def get_current_capacity_used(self):
		"""Calculate total capacity used in bin's UOM"""
		if not self.uom:
			return 0.0
		
		allocations = frappe.db.sql("""
			SELECT 
				cgri.quantity_remaining,
			cgri.stock_uom as uom
			AND cgr.docstatus = 1
			AND cgri.quantity_remaining > 0
		""", self.name, as_dict=1)
		
		total_capacity = 0.0
		
		for allocation in allocations:
			qty = flt(allocation.quantity_remaining)
			uom = allocation.uom
			
			# If UOMs match directly, just add the quantity
			if self.uom == uom:
				total_capacity += qty
			else:
				# For different UOMs, try to convert (simplified - just add as is for now)
				# You may want to add UOM conversion logic here
				total_capacity += qty
		
		return total_capacity
	
	def check_capacity_available(self, quantity, uom):
		"""Check if bin has capacity for additional items"""
		if not self.uom or not self.max_capacity:
			return True  # No capacity limits set
		
		# If UOMs match, directly compare
		if self.uom == uom:
			capacity_needed = quantity
		else:
			# For different UOMs, you may want to add conversion logic here
			# For now, treat as matching
			capacity_needed = quantity
		
		current_used = self.get_current_capacity_used()
		available = self.max_capacity - current_used
		
		return capacity_needed <= available
	
	def get_available_capacity(self):
		"""Get remaining available capacity"""
		if not self.max_capacity:
			return 0.0
		
		current_used = self.get_current_capacity_used()
		return max(0, self.max_capacity - current_used)
	
	@frappe.whitelist()
	def get_current_allocations(self):
		"""Get all current allocations for this bin"""
		allocations = frappe.db.sql("""
			SELECT 
				cgri.parent as goods_receipt,
				cgri.name as receipt_item,
				cgr.customer,
				cgri.customer_reference,
				cgri.description,
			cgri.actual_stock_quantity as original_qty,
			cgri.quantity_remaining,
			cgri.stock_uom as uom,
				cgr.receipt_date,
				DATEDIFF(CURDATE(), cgr.receipt_date) as days_stored
			FROM `tabCustomer Goods Receipt Item` cgri
			INNER JOIN `tabCustomer Goods Receipt` cgr ON cgri.parent = cgr.name
			WHERE cgri.warehouse_bin = %s
			AND cgr.docstatus = 1
			AND cgri.quantity_remaining > 0
			ORDER BY cgr.receipt_date ASC
		""", self.name, as_dict=1)
		
		# Add capacity in bin's UOM to each allocation
		for allocation in allocations:
			qty = flt(allocation.quantity_remaining)
			uom = allocation.uom
			
			# If UOMs match, capacity used equals quantity
			if self.uom == uom:
				allocation.capacity_used = qty
			else:
				# For different UOMs, you may want to add conversion logic
				allocation.capacity_used = qty
		
		return allocations
