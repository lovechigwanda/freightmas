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
	filters["reconciliation_status"] = "Difference"

	conditions, params = get_reconciliation_conditions(filters)
	data = frappe.db.sql(
		"""
		SELECT
			cashier,
			COUNT(*) AS difference_count,
			SUM(CASE WHEN difference > 0 THEN difference ELSE 0 END) AS excess_amount,
			SUM(CASE WHEN difference < 0 THEN ABS(difference) ELSE 0 END) AS shortage_amount,
			SUM(difference) AS net_difference,
			MIN(posting_date) AS first_difference_date,
			MAX(posting_date) AS last_difference_date
		FROM `tabCash Reconciliation`
		WHERE {conditions}
		GROUP BY cashier
		ORDER BY ABS(SUM(difference)) DESC, cashier
		""".format(conditions=conditions),
		params,
		as_dict=True,
	)

	return get_columns(filters), data, None, None, get_summary(data)


def get_columns(filters):
	currency = get_currency(filters)
	return [
		{"label": _("Cashier"), "fieldname": "cashier", "fieldtype": "Link", "options": "User", "width": 220},
		{"label": _("Differences"), "fieldname": "difference_count", "fieldtype": "Int", "width": 100},
		{"label": _("Excess ({0})").format(currency), "fieldname": "excess_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Shortage ({0})").format(currency), "fieldname": "shortage_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Net Difference"), "fieldname": "net_difference", "fieldtype": "Currency", "width": 130},
		{"label": _("First Difference"), "fieldname": "first_difference_date", "fieldtype": "Date", "width": 120},
		{"label": _("Last Difference"), "fieldname": "last_difference_date", "fieldtype": "Date", "width": 120},
	]


def get_summary(data):
	return [
		{"label": _("Cashiers"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Total Differences"), "value": sum(flt(d.difference_count) for d in data), "datatype": "Int", "indicator": "Orange"},
		{"label": _("Net Difference"), "value": sum(flt(d.net_difference) for d in data), "datatype": "Currency", "indicator": "Red"},
	]
