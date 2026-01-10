# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StorageRateCard(Document):
	def validate(self):
		"""Validate Storage Rate Card"""
		self.validate_dates()
		self.validate_default_rate_card()
	
	def validate_dates(self):
		"""Ensure valid_to is after valid_from"""
		if self.valid_from and self.valid_to:
			if self.valid_to < self.valid_from:
				frappe.throw("Valid To date cannot be before Valid From date")
	
	def validate_default_rate_card(self):
		"""Ensure only one default rate card per customer"""
		if self.is_default:
			existing = frappe.db.exists("Storage Rate Card", {
				"is_default": 1,
				"customer": self.customer or "",
				"name": ["!=", self.name]
			})
			if existing:
				if self.customer:
					frappe.throw(f"A default rate card already exists for customer {self.customer}")
				else:
					frappe.throw("A default rate card (General) already exists")
	
	@staticmethod
	def get_applicable_rate_card(customer, date=None):
		"""Get applicable rate card for customer"""
		if not date:
			date = frappe.utils.today()
		
		# First, try to find customer-specific rate card
		rate_card = frappe.db.get_value("Storage Rate Card", {
			"customer": customer,
			"valid_from": ["<=", date],
			"is_default": 1
		}, "name")
		
		if not rate_card:
			# Fall back to general default rate card
			rate_card = frappe.db.get_value("Storage Rate Card", {
				"customer": ["is", "not set"],
				"valid_from": ["<=", date],
				"is_default": 1
			}, "name")
		
		return rate_card
