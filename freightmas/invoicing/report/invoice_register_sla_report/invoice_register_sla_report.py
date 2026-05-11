import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("ID"),
			"fieldtype": "Link",
			"options": "Invoice Register Entry",
			"width": 170,
		},
		{"fieldname": "entry_type", "label": _("Type"), "fieldtype": "Data", "width": 90},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Data", "width": 180},
		{"fieldname": "from_status", "label": _("From Status"), "fieldtype": "Data", "width": 170},
		{"fieldname": "to_status", "label": _("To Status"), "fieldtype": "Data", "width": 170},
		{"fieldname": "changed_at", "label": _("Changed At"), "fieldtype": "Datetime", "width": 160},
		{
			"fieldname": "changed_by",
			"label": _("Changed By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
		{
			"fieldname": "working_days_in_previous_status",
			"label": _("Working Days in Status"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 170,
		},
		{"fieldname": "comment", "label": _("Comment"), "fieldtype": "Data", "width": 250},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql(
		f"""
		SELECT
			ire.name,
			ire.entry_type,
			ire.party,
			isl.from_status,
			isl.to_status,
			isl.changed_at,
			isl.changed_by,
			isl.working_days_in_previous_status,
			isl.comment
		FROM `tabInvoice Register Entry` ire
		INNER JOIN `tabInvoice Status Log` isl ON isl.parent = ire.name
		WHERE ire.docstatus < 2
			{conditions}
		ORDER BY ire.name, isl.changed_at
	""",
		filters,
		as_dict=1,
	)


def get_conditions(filters):
	conditions = ""
	if filters.get("company"):
		conditions += " AND ire.company = %(company)s"
	if filters.get("from_date"):
		conditions += " AND ire.entry_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND ire.entry_date <= %(to_date)s"
	if filters.get("entry_type"):
		conditions += " AND ire.entry_type = %(entry_type)s"
	return conditions
