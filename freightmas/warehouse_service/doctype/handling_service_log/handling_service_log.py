# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class HandlingServiceLog(Document):
	def validate(self):
		"""Validate Handling Service Log"""
		self.calculate_amounts()
	
	def calculate_amounts(self):
		"""Calculate amount for each item"""
		for item in self.items:
			item.amount = flt(item.quantity) * flt(item.rate)
