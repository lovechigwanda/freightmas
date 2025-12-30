# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HandlingActivityType(Document):
	def validate(self):
		"""Validate Handling Activity Type"""
		self.validate_activity_code()
	
	def validate_activity_code(self):
		"""Ensure activity code is uppercase and clean"""
		if self.activity_code:
			self.activity_code = self.activity_code.strip().upper()
