import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Data", "width": 200},
		{"fieldname": "entry_type", "label": _("Type"), "fieldtype": "Data", "width": 90},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
		{"fieldname": "entry_count", "label": _("Entries"), "fieldtype": "Int", "width": 80},
		{
			"fieldname": "total_net",
			"label": _("Net Total"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"fieldname": "total_tax",
			"label": _("Total VAT"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "total_amount",
			"label": _("Total (Incl. VAT)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql(
		f"""
		SELECT
			ire.party,
			ire.entry_type,
			ire.currency,
			COUNT(ire.name) AS entry_count,
			SUM(ire.total_charge_amount) AS total_net,
			SUM(ire.tax_amount) AS total_tax,
			SUM(ire.amount) AS total_amount
		FROM `tabInvoice Register Entry` ire
		WHERE ire.docstatus < 2
			AND ire.status != 'Cancelled'
			{conditions}
		GROUP BY ire.party, ire.entry_type, ire.currency
		ORDER BY ire.party, ire.entry_type
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
	if filters.get("status"):
		conditions += " AND ire.status = %(status)s"
	return conditions
