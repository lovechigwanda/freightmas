# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CustomerGoodsReceipt(Document):
	def validate(self):
		"""Validate and set defaults"""
		self.set_quantity_remaining()
		self.calculate_totals()
	
	def set_quantity_remaining(self):
		"""Set quantity_remaining to quantity for new items"""
		for item in self.items:
			if not item.quantity_remaining:
				item.quantity_remaining = item.quantity
	
	def calculate_totals(self):
		"""Calculate total quantities"""
		self.total_pallets = 0
		self.total_weight_kg = 0
		self.total_volume_cbm = 0
		
		for item in self.items:
			if item.storage_unit_type == "Pallet":
				self.total_pallets += item.quantity or 0
			self.total_weight_kg += (item.weight_kg or 0) * (item.quantity or 0)
			self.total_volume_cbm += (item.volume_cbm or 0) * (item.quantity or 0)
