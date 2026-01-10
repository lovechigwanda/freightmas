# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StorageUnitType(Document):
	def validate(self):
		"""Validate Storage Unit Type"""
		self.calculate_volume()
	
	def calculate_volume(self):
		"""Calculate volume in CBM from dimensions"""
		if self.standard_length_cm and self.standard_width_cm and self.standard_height_cm:
			# Convert cm³ to m³ (divide by 1,000,000)
			self.standard_volume_cbm = (
				self.standard_length_cm * 
				self.standard_width_cm * 
				self.standard_height_cm
			) / 1000000
