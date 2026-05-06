# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from freightmas.freightmas.report.cash_reconciliation_common import (
	get_cash_ledger_balance,
	get_currency,
	get_reconciliation_conditions,
	validate_company,
)


def execute(filters=None):
	filters = filters or {}
	validate_company(filters)
	if not filters.get("as_of_date"):
		filters["as_of_date"] = getdate()

	conditions, params = get_reconciliation_conditions(filters)
	data = frappe.db.sql(
		"""
		SELECT
			name,
			posting_date,
			posting_time,
			cash_account,
			COALESCE(branch, '') AS branch,
			cashier,
			ledger_balance AS reconciled_ledger_balance,
			physical_cash_balance,
			difference AS reconciliation_difference,
			reconciliation_status
		FROM `tabCash Reconciliation`
		WHERE {conditions}
		ORDER BY cash_account, posting_date DESC, posting_time DESC
		""".format(conditions=conditions),
		params,
		as_dict=True,
	)

	for row in data:
		current_ledger_balance = get_cash_ledger_balance(filters.get("company"), row.cash_account, filters.get("as_of_date"))
		row.current_ledger_balance = current_ledger_balance
		row.ledger_movement_since_reconciliation = flt(current_ledger_balance) - flt(row.reconciled_ledger_balance)
		row.current_ledger_vs_physical = flt(current_ledger_balance) - flt(row.physical_cash_balance)

	return get_columns(filters), data, None, None, get_summary(data)


def get_columns(filters):
	currency = get_currency(filters)
	return [
		{"label": _("Reconciliation"), "fieldname": "name", "fieldtype": "Link", "options": "Cash Reconciliation", "width": 190},
		{"label": _("Reconciliation Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 130},
		{"label": _("Cash Account"), "fieldname": "cash_account", "fieldtype": "Link", "options": "Account", "width": 220},
		{"label": _("Branch / Station"), "fieldname": "branch", "fieldtype": "Data", "width": 140},
		{"label": _("Cashier"), "fieldname": "cashier", "fieldtype": "Link", "options": "User", "width": 180},
		{"label": _("Reconciled Ledger ({0})").format(currency), "fieldname": "reconciled_ledger_balance", "fieldtype": "Currency", "width": 150},
		{"label": _("Physical ({0})").format(currency), "fieldname": "physical_cash_balance", "fieldtype": "Currency", "width": 130},
		{"label": _("Reconciliation Difference"), "fieldname": "reconciliation_difference", "fieldtype": "Currency", "width": 160},
		{"label": _("Current Ledger"), "fieldname": "current_ledger_balance", "fieldtype": "Currency", "width": 130},
		{"label": _("Ledger Movement"), "fieldname": "ledger_movement_since_reconciliation", "fieldtype": "Currency", "width": 130},
		{"label": _("Current Ledger vs Physical"), "fieldname": "current_ledger_vs_physical", "fieldtype": "Currency", "width": 170},
		{"label": _("Status"), "fieldname": "reconciliation_status", "fieldtype": "Data", "width": 100},
	]


def get_summary(data):
	return [
		{"label": _("Reconciliations"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Total Current Ledger"), "value": sum(flt(d.current_ledger_balance) for d in data), "datatype": "Currency", "indicator": "Green"},
		{"label": _("Current Ledger vs Physical"), "value": sum(flt(d.current_ledger_vs_physical) for d in data), "datatype": "Currency", "indicator": "Orange"},
	]
