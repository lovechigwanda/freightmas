# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class CustomerWarehouseRates(Document):
	def validate(self):
		"""Validate rate card"""
		if self.valid_to and self.valid_from:
			if getdate(self.valid_to) < getdate(self.valid_from):
				frappe.throw("Valid To date cannot be before Valid From date")
	
	@staticmethod
	def get_storage_rate(customer, storage_unit_type, bay=None, date=None):
		"""Get applicable storage rate for customer
		
		Hierarchy:
		1. Customer + Specific Bay + Storage Unit Type
		2. Customer + Bay Type + Storage Unit Type
		3. Customer + Storage Unit Type
		4. Storage Unit Type default rate
		"""
		if not date:
			date = today()
		
		filters = {
			"customer": customer,
			"storage_unit_type": storage_unit_type,
			"is_active": 1,
			"valid_from": ["<=", date]
		}
		
		# Try specific bay first
		if bay:
			bay_filters = filters.copy()
			bay_filters["specific_bay"] = bay
			rate = frappe.db.get_value("Customer Warehouse Rates", bay_filters, 
				["storage_rate_per_day", "storage_rate_per_month"], as_dict=True)
			if rate:
				return rate
			
			# Try bay type
			bay_type = frappe.db.get_value("Warehouse Bay", bay, "bay_type")
			if bay_type:
				bay_type_filters = filters.copy()
				bay_type_filters["apply_to_bay_type"] = bay_type
				rate = frappe.db.get_value("Customer Warehouse Rates", bay_type_filters,
					["storage_rate_per_day", "storage_rate_per_month"], as_dict=True)
				if rate:
					return rate
		
		# Try customer + storage unit type
		rate = frappe.db.get_value("Customer Warehouse Rates", filters,
			["storage_rate_per_day", "storage_rate_per_month"], as_dict=True)
		if rate:
			return rate
		
		# Fall back to storage unit type default
		return frappe.db.get_value("Storage Unit Type", storage_unit_type,
			["default_storage_rate_per_day as storage_rate_per_day", 
			 "default_storage_rate_per_month as storage_rate_per_month"], as_dict=True)
	
	@staticmethod
	def get_handling_rate(customer, handling_service_type, date=None):
		"""Get applicable handling rate for customer
		
		Hierarchy:
		1. Customer-specific rate
		2. Handling Service Type default rate
		"""
		if not date:
			date = today()
		
		# Try customer-specific rate
		rate = frappe.db.get_value("Customer Warehouse Rates", {
			"customer": customer,
			"handling_service_type": handling_service_type,
			"is_active": 1,
			"valid_from": ["<=", date]
		}, ["handling_rate", "handling_unit"], as_dict=True)
		
		if rate:
			return rate
		
		# Fall back to service type default
		return frappe.db.get_value("Handling Service Type", handling_service_type,
			["default_rate as handling_rate", "default_unit as handling_unit"], as_dict=True)
