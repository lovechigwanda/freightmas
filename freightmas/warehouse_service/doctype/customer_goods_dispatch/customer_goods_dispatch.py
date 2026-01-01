# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CustomerGoodsDispatch(Document):
	def on_submit(self):
		"""Update quantity_remaining in receipt items when dispatch is submitted"""
		self.update_receipt_items()
	
	def on_cancel(self):
		"""Restore quantity_remaining in receipt items when dispatch is cancelled"""
		self.update_receipt_items(cancel=True)
	
	def update_receipt_items(self, cancel=False):
		"""Update quantity remaining in linked receipt items"""
		for item in self.items:
			if item.warehouse_bin:
				# Find matching receipt items in the same bin
				receipt_items = frappe.db.sql("""
					SELECT gri.name, gri.quantity_remaining, gri.quantity
					FROM `tabCustomer Goods Receipt Item` gri
					INNER JOIN `tabCustomer Goods Receipt` gr ON gr.name = gri.parent
					WHERE gr.warehouse_job = %(job)s
					AND gr.docstatus = 1
					AND gri.storage_unit_type = %(unit_type)s
					AND gri.warehouse_bin = %(bin)s
					AND gri.quantity_remaining > 0
					ORDER BY gr.receipt_date ASC, gr.creation ASC
				""", {
					"job": self.warehouse_job,
					"unit_type": item.storage_unit_type,
					"bin": item.warehouse_bin
				}, as_dict=1)
				
				remaining_to_dispatch = item.quantity
				
				for receipt_item in receipt_items:
					if remaining_to_dispatch <= 0:
						break
					
					if cancel:
						# Restore quantity when cancelling dispatch
						new_remaining = min(
							receipt_item.quantity_remaining + remaining_to_dispatch,
							receipt_item.quantity
						)
						qty_restored = new_remaining - receipt_item.quantity_remaining
						remaining_to_dispatch -= qty_restored
					else:
						# Reduce quantity when submitting dispatch
						qty_to_reduce = min(remaining_to_dispatch, receipt_item.quantity_remaining)
						new_remaining = receipt_item.quantity_remaining - qty_to_reduce
						remaining_to_dispatch -= qty_to_reduce
					
					frappe.db.set_value(
						'Customer Goods Receipt Item',
						receipt_item.name,
						'quantity_remaining',
						new_remaining
					)
