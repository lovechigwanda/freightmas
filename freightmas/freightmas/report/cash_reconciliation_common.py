# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def validate_company(filters):
	if not filters.get("company"):
		frappe.throw(_("Company is required"))


def get_currency(filters):
	if filters.get("company"):
		return frappe.get_cached_value("Company", filters.get("company"), "default_currency")
	return frappe.defaults.get_global_default("currency") or "USD"


def get_reconciliation_conditions(filters, include_docstatus=True, default_docstatus=1):
	conditions = []
	params = {}

	if filters.get("company"):
		conditions.append("company = %(company)s")
		params["company"] = filters.get("company")

	if filters.get("from_date"):
		conditions.append("posting_date >= %(from_date)s")
		params["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("posting_date <= %(to_date)s")
		params["to_date"] = filters.get("to_date")

	if filters.get("cash_account"):
		conditions.append("cash_account = %(cash_account)s")
		params["cash_account"] = filters.get("cash_account")

	if filters.get("cashier"):
		conditions.append("cashier = %(cashier)s")
		params["cashier"] = filters.get("cashier")

	if filters.get("branch"):
		conditions.append("branch = %(branch)s")
		params["branch"] = filters.get("branch")

	if filters.get("reconciliation_status"):
		conditions.append("reconciliation_status = %(reconciliation_status)s")
		params["reconciliation_status"] = filters.get("reconciliation_status")

	if include_docstatus:
		docstatus = filters.get("docstatus")
		if docstatus in (0, 1, 2, "0", "1", "2"):
			docstatus = int(docstatus)
		else:
			docstatus = default_docstatus
		conditions.append("docstatus = %(docstatus)s")
		params["docstatus"] = docstatus

	return " AND ".join(conditions) or "1=1", params


def get_cash_ledger_balance(company, cash_account, posting_date):
	balance = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(debit - credit), 0)
		FROM `tabGL Entry`
		WHERE company = %(company)s
			AND account = %(cash_account)s
			AND posting_date <= %(posting_date)s
			AND is_cancelled = 0
		""",
		{
			"company": company,
			"cash_account": cash_account,
			"posting_date": posting_date,
		},
	)[0][0]
	return flt(balance, 2)


def get_cash_account_filter():
	return {
		"fieldname": "cash_account",
		"label": _("Cash Account"),
		"fieldtype": "Link",
		"options": "Account",
	}
