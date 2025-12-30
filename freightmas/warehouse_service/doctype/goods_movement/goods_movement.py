# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GoodsMovement(Document):
	def validate(self):
		"""Validate Goods Movement"""
		self.validate_movement_type()
	
	def validate_movement_type(self):
		"""Validate source and destination based on movement type"""
		if self.movement_type == "Inbound":
			if not self.destination_bay:
				frappe.throw("Destination Bay is required for Inbound movements")
		
		elif self.movement_type == "Outbound":
			if not self.source_bay:
				frappe.throw("Source Bay is required for Outbound movements")
		
		elif self.movement_type in ["Relocation", "Consolidation"]:
			if not self.source_bay or not self.destination_bay:
				frappe.throw("Both Source and Destination Bays are required for this movement type")
