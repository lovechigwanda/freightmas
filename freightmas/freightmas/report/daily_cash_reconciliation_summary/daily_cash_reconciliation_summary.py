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

	columns = get_columns(filters)
	conditions, params = get_reconciliation_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			posting_date,
			company,
			COALESCE(branch, '') AS branch,
			COUNT(*) AS reconciliations,
			SUM(CASE WHEN reconciliation_status = 'Balanced' THEN 1 ELSE 0 END) AS balanced_count,
			SUM(CASE WHEN reconciliation_status = 'Difference' THEN 1 ELSE 0 END) AS difference_count,
			SUM(ledger_balance) AS ledger_balance,
			SUM(physical_cash_balance) AS physical_cash_balance,
			SUM(difference) AS net_difference,
			SUM(CASE WHEN difference > 0 THEN difference ELSE 0 END) AS excess_amount,
			SUM(CASE WHEN difference < 0 THEN ABS(difference) ELSE 0 END) AS shortage_amount
		FROM `tabCash Reconciliation`
		WHERE {conditions}
		GROUP BY posting_date, company, branch
		ORDER BY posting_date DESC, branch
		""".format(conditions=conditions),
		params,
		as_dict=True,
	)

	return columns, data, None, None, get_summary(data)


def get_columns(filters):
	currency = get_currency(filters)
	return [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 180},
		{"label": _("Branch / Station"), "fieldname": "branch", "fieldtype": "Data", "width": 140},
		{"label": _("Count"), "fieldname": "reconciliations", "fieldtype": "Int", "width": 80},
		{"label": _("Balanced"), "fieldname": "balanced_count", "fieldtype": "Int", "width": 90},
		{"label": _("With Difference"), "fieldname": "difference_count", "fieldtype": "Int", "width": 120},
		{"label": _("Ledger ({0})").format(currency), "fieldname": "ledger_balance", "fieldtype": "Currency", "width": 130},
		{"label": _("Physical ({0})").format(currency), "fieldname": "physical_cash_balance", "fieldtype": "Currency", "width": 130},
		{"label": _("Net Difference"), "fieldname": "net_difference", "fieldtype": "Currency", "width": 130},
		{"label": _("Excess"), "fieldname": "excess_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Shortage"), "fieldname": "shortage_amount", "fieldtype": "Currency", "width": 120},
	]


def get_summary(data):
	return [
		{"label": _("Reconciliations"), "value": sum(flt(d.reconciliations) for d in data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("With Differences"), "value": sum(flt(d.difference_count) for d in data), "datatype": "Int", "indicator": "Orange"},
		{"label": _("Net Difference"), "value": sum(flt(d.net_difference) for d in data), "datatype": "Currency", "indicator": "Green"},
	]
