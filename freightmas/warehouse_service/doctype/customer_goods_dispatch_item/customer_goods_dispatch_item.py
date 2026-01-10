# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CustomerGoodsDispatchItem(Document):
	pass


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bin_query(doctype, txt, searchfield, start, page_len, filters):
	"""Filter warehouse bins based on the selected warehouse bay"""
	warehouse_bay = filters.get("warehouse_bay")
	
	if not warehouse_bay:
		return []
	
	return frappe.db.sql("""
		SELECT name, bin_number
		FROM `tabWarehouse Bin`
		WHERE warehouse_bay = %(warehouse_bay)s
		AND (name LIKE %(txt)s OR bin_number LIKE %(txt)s)
		ORDER BY bin_number
		LIMIT %(start)s, %(page_len)s
	""", {
		"warehouse_bay": warehouse_bay,
		"txt": "%" + txt + "%",
		"start": start,
		"page_len": page_len
	})
