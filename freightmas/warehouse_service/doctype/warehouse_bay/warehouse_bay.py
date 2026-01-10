# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class WarehouseBay(Document):
	def validate(self):
		"""Validate Warehouse Bay"""
		self.validate_bay_code()
		self.validate_capacity_limits()
	
	def validate_bay_code(self):
		"""Ensure bay code is uppercase and clean"""
		if self.bay_code:
			self.bay_code = self.bay_code.strip().upper()
	
	def validate_capacity_limits(self):
		"""Ensure capacity limits are positive if set"""
		if self.capacity_sqm and self.capacity_sqm < 0:
			frappe.throw("Capacity (SQM) cannot be negative")
		
		if self.max_pallets and self.max_pallets < 0:
			frappe.throw("Max Pallet Positions cannot be negative")
		
		if self.max_weight_kg and self.max_weight_kg < 0:
			frappe.throw("Max Weight cannot be negative")
		
		if self.max_height_cm and self.max_height_cm < 0:
			frappe.throw("Max Height cannot be negative")
	
	def get_total_bin_capacity(self):
		"""Calculate total capacity allocated to bins in this bay"""
		result = frappe.db.sql("""
			SELECT 
				SUM(CASE WHEN capacity_uom = 'Pallets' THEN max_capacity ELSE 0 END) as total_pallets,
				SUM(CASE WHEN capacity_uom = 'SQM' THEN max_capacity ELSE 0 END) as total_sqm,
				SUM(max_weight_kg) as total_weight
			FROM `tabWarehouse Bin`
			WHERE bay = %s
		""", self.bay_code, as_dict=1)
		
		if result:
			return {
				'total_pallets': flt(result[0].get('total_pallets', 0), 2),
				'total_sqm': flt(result[0].get('total_sqm', 0), 2),
				'total_weight': flt(result[0].get('total_weight', 0), 2)
			}
		
		return {'total_pallets': 0, 'total_sqm': 0, 'total_weight': 0}


@frappe.whitelist()
def get_bay_with_bins(bay_code):
	"""Get bay information with all bins and capacity summary"""
	
	# Get bay document
	bay = frappe.get_doc("Warehouse Bay", bay_code)
	
	# Get summary statistics
	summary = frappe.db.sql("""
		SELECT 
			COUNT(*) as total_bins,
			SUM(CASE WHEN current_capacity_used > 0 THEN 1 ELSE 0 END) as occupied_bins,
			SUM(CASE WHEN current_capacity_used = 0 OR current_capacity_used IS NULL THEN 1 ELSE 0 END) as available_bins,
			AVG(CASE WHEN max_capacity > 0 THEN capacity_utilization_pct ELSE 0 END) as avg_utilization
		FROM `tabWarehouse Bin`
		WHERE bay = %s
	""", bay_code, as_dict=1)
	
	# Get capacity breakdown by UOM
	capacity_by_uom = frappe.db.sql("""
		SELECT 
			uom as capacity_uom,
			COUNT(*) as bin_count,
			SUM(max_capacity) as max_capacity,
			SUM(current_capacity_used) as used_capacity
		FROM `tabWarehouse Bin`
		WHERE bay = %s
		AND uom IS NOT NULL
		AND max_capacity > 0
		GROUP BY uom
		ORDER BY uom
	""", bay_code, as_dict=1)
	
	# Get all bins
	bins = frappe.db.sql("""
		SELECT 
			bin_code,
			bin_type,
			uom as capacity_uom,
			max_capacity,
			current_capacity_used,
			capacity_utilization_pct,
			CASE WHEN current_capacity_used > 0 THEN 1 ELSE 0 END as is_occupied,
			max_weight_kg
		FROM `tabWarehouse Bin`
		WHERE bay = %s
		ORDER BY bin_code ASC
	""", bay_code, as_dict=1)
	
	# Clean up numeric fields
	for bin in bins:
		bin['max_capacity'] = flt(bin.get('max_capacity', 0), 2)
		bin['current_capacity_used'] = flt(bin.get('current_capacity_used', 0), 2)
		bin['capacity_utilization_pct'] = flt(bin.get('capacity_utilization_pct', 0), 1)
		bin['max_weight_kg'] = flt(bin.get('max_weight_kg', 0), 2)
	
	for uom in capacity_by_uom:
		uom['max_capacity'] = flt(uom.get('max_capacity', 0), 2)
		uom['used_capacity'] = flt(uom.get('used_capacity', 0), 2)
	
	return {
		'bay': {
			'bay_code': bay.bay_code,
			'bay_type': bay.bay_type,
			'capacity_sqm': flt(bay.capacity_sqm, 2),
			'is_available': bay.is_available
		},
		'summary': {
			'total_bins': summary[0].get('total_bins', 0) if summary else 0,
			'occupied_bins': summary[0].get('occupied_bins', 0) if summary else 0,
			'available_bins': summary[0].get('available_bins', 0) if summary else 0,
			'avg_utilization': flt(summary[0].get('avg_utilization', 0), 1) if summary else 0
		},
		'capacity_by_uom': capacity_by_uom,
		'bins': bins
	}
