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
		{"fieldname": "entry_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "entry_type", "label": _("Type"), "fieldtype": "Data", "width": 90},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 170},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Data", "width": 180},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "sla_due_at",
			"label": _("SLA Due At"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "hours_overdue",
			"label": _("Hours Overdue"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 130,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql(
		f"""
		SELECT
			ire.name,
			ire.entry_date,
			ire.entry_type,
			ire.status,
			ire.party,
			ire.currency,
			ire.amount,
			ire.sla_due_at,
			ROUND(TIMESTAMPDIFF(MINUTE, ire.sla_due_at, NOW()) / 60.0, 1) AS hours_overdue
		FROM `tabInvoice Register Entry` ire
		WHERE ire.is_overdue = 1
			AND ire.docstatus < 2
			{conditions}
		ORDER BY ire.sla_due_at ASC
	""",
		filters,
		as_dict=1,
	)


def get_conditions(filters):
	conditions = ""
	if filters.get("company"):
		conditions += " AND ire.company = %(company)s"
	if filters.get("entry_type"):
		conditions += " AND ire.entry_type = %(entry_type)s"
	return conditions
