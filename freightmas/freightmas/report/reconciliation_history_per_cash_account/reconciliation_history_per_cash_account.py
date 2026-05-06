# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from freightmas.freightmas.report.cash_reconciliation_common import (
	get_currency,
	get_reconciliation_conditions,
	validate_company,
)


def execute(filters=None):
	filters = filters or {}
	validate_company(filters)

	conditions, params = get_reconciliation_conditions(filters, default_docstatus=1)
	data = frappe.db.sql(
		"""
		SELECT
			name,
			posting_date,
			posting_time,
			cash_account,
			COALESCE(branch, '') AS branch,
			cashier,
			ledger_balance,
			physical_cash_balance,
			difference,
			reconciliation_status,
			approved_by,
			approved_on,
			remarks
		FROM `tabCash Reconciliation`
		WHERE {conditions}
		ORDER BY cash_account, posting_date DESC, posting_time DESC, name DESC
		""".format(conditions=conditions),
		params,
		as_dict=True,
	)

	return get_columns(filters), data, None, None, get_summary(data)


def get_columns(filters):
	currency = get_currency(filters)
	return [
		{"label": _("Reconciliation"), "fieldname": "name", "fieldtype": "Link", "options": "Cash Reconciliation", "width": 190},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Time"), "fieldname": "posting_time", "fieldtype": "Time", "width": 90},
		{"label": _("Cash Account"), "fieldname": "cash_account", "fieldtype": "Link", "options": "Account", "width": 220},
		{"label": _("Branch / Station"), "fieldname": "branch", "fieldtype": "Data", "width": 140},
		{"label": _("Cashier"), "fieldname": "cashier", "fieldtype": "Link", "options": "User", "width": 180},
		{"label": _("Ledger ({0})").format(currency), "fieldname": "ledger_balance", "fieldtype": "Currency", "width": 120},
		{"label": _("Physical ({0})").format(currency), "fieldname": "physical_cash_balance", "fieldtype": "Currency", "width": 120},
		{"label": _("Difference"), "fieldname": "difference", "fieldtype": "Currency", "width": 120},
		{"label": _("Status"), "fieldname": "reconciliation_status", "fieldtype": "Data", "width": 100},
		{"label": _("Approved By"), "fieldname": "approved_by", "fieldtype": "Link", "options": "User", "width": 170},
		{"label": _("Approved On"), "fieldname": "approved_on", "fieldtype": "Datetime", "width": 160},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Small Text", "width": 260},
	]


def get_summary(data):
	return [
		{"label": _("Submitted Reconciliations"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Net Difference"), "value": sum(flt(d.difference) for d in data), "datatype": "Currency", "indicator": "Orange"},
	]
