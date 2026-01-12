import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_job_order_reference_fields():
	"""Create job_order_reference custom fields in Quotation and Forwarding Job"""
	
	custom_fields = {
		"Quotation": [
			{
				"fieldname": "job_order_reference",
				"label": "Job Order Reference",
				"fieldtype": "Link",
				"options": "Job Order",
				"insert_after": "party_name",
				"read_only": 1,
				"allow_on_submit": 1,
				"translatable": 0
			}
		],
		"Forwarding Job": [
			{
				"fieldname": "job_order_reference",
				"label": "Job Order Reference",
				"fieldtype": "Link",
				"options": "Job Order",
				"insert_after": "naming_series",
				"read_only": 1,
				"allow_on_submit": 1,
				"translatable": 0
			}
		]
	}
	
	create_custom_fields(custom_fields, update=True)
	frappe.db.commit()
	print("Custom fields created successfully!")
