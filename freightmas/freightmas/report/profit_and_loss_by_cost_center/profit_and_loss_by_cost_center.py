# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cstr

from erpnext.accounts.report.financial_statements import (
	get_accounts,
	filter_accounts,
	filter_out_zero_value_rows,
	set_gl_entries_by_account,
)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
	get_net_profit_loss,
)


def execute(filters=None):
	if not filters:
		filters = frappe._dict()

	validate_filters(filters)

	# Get cost centers for the company
	cost_center_list = get_cost_center_list(filters)

	if not cost_center_list:
		frappe.msgprint(_("No Cost Centers found for the selected company"))
		return [], []

	# Get columns dynamically based on cost centers
	columns = get_columns(cost_center_list, filters)

	# Get income and expense data
	income, expense = get_income_expense_data(filters, cost_center_list)

	# Build data with proper hierarchy
	data = []

	# Add Income section
	if income:
		data.extend(income)

	# Add Expense section
	if expense:
		data.extend(expense)

	# Calculate and add Net Profit/Loss
	net_profit_loss = calculate_net_profit_loss(income, expense, cost_center_list, filters)
	if net_profit_loss:
		data.append(net_profit_loss)

	# Generate chart data
	chart = get_chart_data(income, expense, cost_center_list)

	return columns, data, None, chart


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("Company is mandatory"))

	if not filters.get("from_date"):
		frappe.throw(_("From Date is mandatory"))

	if not filters.get("to_date"):
		frappe.throw(_("To Date is mandatory"))

	if filters.get("from_date") > filters.get("to_date"):
		frappe.throw(_("From Date cannot be greater than To Date"))


def get_cost_center_list(filters):
	"""Get list of cost centers for the company"""
	conditions = {"company": filters.get("company"), "is_group": 0}

	# If specific cost centers are selected, filter by them
	if filters.get("cost_center"):
		selected_cost_centers = filters.get("cost_center")
		if isinstance(selected_cost_centers, str):
			selected_cost_centers = [selected_cost_centers]
		if selected_cost_centers:
			conditions["name"] = ("in", selected_cost_centers)

	cost_centers = frappe.get_all(
		"Cost Center",
		filters=conditions,
		fields=["name", "cost_center_name"],
		order_by="lft",
	)

	cost_center_list = []
	for cc in cost_centers:
		cost_center_list.append(
			frappe._dict(
				{
					"name": cc.name,
					"label": cc.cost_center_name or cc.name.split(" - ")[0],
					"key": frappe.scrub(cc.name),
				}
			)
		)

	return cost_center_list


def get_columns(cost_center_list, filters):
	"""Generate columns dynamically based on cost centers"""
	company_currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")
	currency = filters.get("presentation_currency") or company_currency

	columns = [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		}
	]

	# Add a column for each cost center
	for cc in cost_center_list:
		columns.append(
			{
				"fieldname": cc.key,
				"label": cc.label,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			}
		)

	# Add total column
	columns.append(
		{
			"fieldname": "total",
			"label": _("Total"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		}
	)

	# Add currency column (hidden, used for currency formatting)
	columns.append(
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		}
	)

	return columns


def get_income_expense_data(filters, cost_center_list):
	"""Get income and expense data with cost center breakdown"""
	company = filters.get("company")
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	currency = filters.get("presentation_currency") or company_currency

	# Get income data
	income = get_data_for_root_type(
		filters, cost_center_list, "Income", "Credit", currency
	)

	# Get expense data
	expense = get_data_for_root_type(
		filters, cost_center_list, "Expense", "Debit", currency
	)

	return income, expense


def get_data_for_root_type(filters, cost_center_list, root_type, balance_must_be, currency):
	"""Get hierarchical account data for a specific root type (Income/Expense)"""
	company = filters.get("company")

	# Get accounts for this root type
	accounts = get_accounts(company, root_type)
	if not accounts:
		return []

	# Build account hierarchy
	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	# Get GL entries grouped by account and cost center
	gl_entries = get_gl_entries_by_cost_center(filters, root_type)

	# Distribute GL entries to accounts by cost center
	for entry in gl_entries:
		account_name = entry.account
		cost_center = entry.cost_center

		if account_name in accounts_by_name:
			account = accounts_by_name[account_name]
			cc_key = get_cost_center_key(cost_center, cost_center_list)

			if cc_key:
				# Calculate the value based on debit/credit
				if balance_must_be == "Credit":
					value = flt(entry.credit) - flt(entry.debit)
				else:
					value = flt(entry.debit) - flt(entry.credit)

				account[cc_key] = flt(account.get(cc_key, 0)) + value

	# Accumulate values into parent accounts
	accumulate_values_into_parents(accounts, accounts_by_name, cost_center_list)

	# Calculate totals for each account row
	for account in accounts:
		total = 0
		for cc in cost_center_list:
			total += flt(account.get(cc.key, 0))
		account["total"] = total
		account["currency"] = currency

	# Filter out zero value rows
	data = prepare_data(accounts, parent_children_map, cost_center_list, root_type)
	data = filter_out_zero_value_rows(data, parent_children_map, show_zero_values=False)

	return data


def get_gl_entries_by_cost_center(filters, root_type):
	"""Fetch GL entries grouped by account and cost center"""
	conditions = get_gl_conditions(filters)

	gl_entries = frappe.db.sql(
		"""
		SELECT
			gl.account,
			gl.cost_center,
			SUM(gl.debit) as debit,
			SUM(gl.credit) as credit,
			SUM(gl.debit_in_account_currency) as debit_in_account_currency,
			SUM(gl.credit_in_account_currency) as credit_in_account_currency
		FROM `tabGL Entry` gl
		INNER JOIN `tabAccount` acc ON acc.name = gl.account
		WHERE
			gl.company = %(company)s
			AND gl.posting_date >= %(from_date)s
			AND gl.posting_date <= %(to_date)s
			AND gl.is_cancelled = 0
			AND acc.root_type = %(root_type)s
			{conditions}
		GROUP BY gl.account, gl.cost_center
	""".format(
			conditions=conditions
		),
		{
			"company": filters.get("company"),
			"from_date": filters.get("from_date"),
			"to_date": filters.get("to_date"),
			"root_type": root_type,
		},
		as_dict=True,
	)

	return gl_entries


def get_gl_conditions(filters):
	"""Build additional GL entry conditions"""
	conditions = []

	# Ignore closing entries unless specified
	if not filters.get("include_closing_entries"):
		conditions.append("ifnull(gl.voucher_type, '') != 'Period Closing Voucher'")

	# Filter by specific cost centers if provided
	if filters.get("cost_center"):
		selected = filters.get("cost_center")
		if isinstance(selected, str):
			selected = [selected]
		if selected:
			conditions.append(
				"gl.cost_center IN ({})".format(
					", ".join(["'{}'".format(frappe.db.escape(cc)) for cc in selected])
				)
			)

	# Include default book entries
	if filters.get("include_default_book_entries"):
		conditions.append(
			"""(
				gl.finance_book IS NULL
				OR gl.finance_book = ''
				OR gl.finance_book IN (SELECT default_finance_book FROM `tabCompany` WHERE name = %(company)s)
			)"""
		)

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_cost_center_key(cost_center, cost_center_list):
	"""Get the column key for a cost center"""
	if not cost_center:
		return None

	for cc in cost_center_list:
		if cc.name == cost_center:
			return cc.key

	return None


def accumulate_values_into_parents(accounts, accounts_by_name, cost_center_list):
	"""Accumulate child account values into parent accounts"""
	for d in reversed(accounts):
		if d.parent_account and d.parent_account in accounts_by_name:
			parent = accounts_by_name[d.parent_account]
			for cc in cost_center_list:
				parent[cc.key] = flt(parent.get(cc.key, 0)) + flt(d.get(cc.key, 0))


def prepare_data(accounts, parent_children_map, cost_center_list, root_type):
	"""Prepare data with proper formatting for the report"""
	data = []

	for account in accounts:
		row = frappe._dict(
			{
				"account": account.name,
				"parent_account": account.parent_account,
				"indent": account.indent,
				"account_name": account.account_name,
				"root_type": root_type,
				"is_group": account.is_group,
				"opening_balance": 0,
				"currency": account.get("currency"),
				"total": flt(account.get("total", 0)),
			}
		)

		# Add cost center values
		for cc in cost_center_list:
			row[cc.key] = flt(account.get(cc.key, 0))

		data.append(row)

	return data


def calculate_net_profit_loss(income, expense, cost_center_list, filters):
	"""Calculate net profit/loss row"""
	company = filters.get("company")
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	currency = filters.get("presentation_currency") or company_currency

	net_profit_loss = frappe._dict(
		{
			"account": _("'Profit for the year'"),
			"indent": 0,
			"currency": currency,
			"total": 0,
			"is_group": 0,
			"warn_if_negative": True,
		}
	)

	# Calculate totals for income
	income_totals = {}
	for cc in cost_center_list:
		income_totals[cc.key] = 0

	if income:
		for row in income:
			if row.get("indent") == 0:  # Only take root level accounts
				for cc in cost_center_list:
					income_totals[cc.key] += flt(row.get(cc.key, 0))

	# Calculate totals for expense
	expense_totals = {}
	for cc in cost_center_list:
		expense_totals[cc.key] = 0

	if expense:
		for row in expense:
			if row.get("indent") == 0:  # Only take root level accounts
				for cc in cost_center_list:
					expense_totals[cc.key] += flt(row.get(cc.key, 0))

	# Calculate net profit/loss per cost center
	total_net = 0
	for cc in cost_center_list:
		net_value = income_totals.get(cc.key, 0) - expense_totals.get(cc.key, 0)
		net_profit_loss[cc.key] = net_value
		total_net += net_value

	net_profit_loss["total"] = total_net

	return net_profit_loss


def get_chart_data(income, expense, cost_center_list):
	"""Generate chart data for the report"""
	labels = [cc.label for cc in cost_center_list]

	income_data = []
	expense_data = []
	net_profit_data = []

	for cc in cost_center_list:
		# Sum root level income accounts
		cc_income = 0
		if income:
			for row in income:
				if row.get("indent") == 0:
					cc_income += flt(row.get(cc.key, 0))

		# Sum root level expense accounts
		cc_expense = 0
		if expense:
			for row in expense:
				if row.get("indent") == 0:
					cc_expense += flt(row.get(cc.key, 0))

		income_data.append(cc_income)
		expense_data.append(cc_expense)
		net_profit_data.append(cc_income - cc_expense)

	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Income"), "values": income_data},
				{"name": _("Expense"), "values": expense_data},
				{"name": _("Net Profit/Loss"), "values": net_profit_data},
			],
		},
		"type": "bar",
		"colors": ["#5e64ff", "#ff5858", "#28a745"],
		"barOptions": {"stacked": 0},
	}

	return chart
