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
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 140,
		},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Data", "width": 180},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
		{
			"fieldname": "total_charge_amount",
			"label": _("Net Total"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"fieldname": "tax_amount",
			"label": _("VAT"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
		},
		{
			"fieldname": "amount",
			"label": _("Total (Incl. VAT)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{"fieldname": "linked_invoice", "label": _("Linked Invoice"), "fieldtype": "Data", "width": 170},
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
			ire.company,
			ire.party,
			ire.currency,
			ire.total_charge_amount,
			ire.tax_amount,
			ire.amount,
			COALESCE(ire.linked_sales_invoice, ire.linked_purchase_invoice) AS linked_invoice
		FROM `tabInvoice Register Entry` ire
		WHERE ire.docstatus < 2
		{conditions}
		ORDER BY ire.entry_date DESC, ire.name DESC
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
	if filters.get("party"):
		conditions += " AND ire.party = %(party)s"
	return conditions
