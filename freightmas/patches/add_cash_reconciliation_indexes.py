# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Add database indexes for cash reconciliation queries.

These indexes optimize:
1. GL Entry queries for ledger balance calculations
2. Cash Reconciliation queries for reports and unique constraints
"""

import frappe
from frappe.database import add_index


def execute():
	"""Add indexes to improve query performance."""
	
	# Index for GL Entry queries used in get_cash_ledger_balance
	# Covers: company, account, posting_date, is_cancelled WHERE clause
	add_index(
		"GL Entry",
		["company", "account", "posting_date", "is_cancelled"],
		index_name="idx_gl_entry_cash_balance"
	)
	
	# Index for Cash Reconciliation queries used in reports
	# Covers: company, posting_date, docstatus for daily summaries
	add_index(
		"Cash Reconciliation",
		["company", "posting_date", "docstatus"],
		index_name="idx_cash_recon_summary"
	)
	
	# Index for branch-level reporting queries
	add_index(
		"Cash Reconciliation",
		["branch", "reconciliation_status", "posting_date"],
		index_name="idx_cash_recon_branch"
	)
	
	frappe.log_error(
		"Indexes added for Cash Reconciliation and GL Entry tables",
		title="Cash Reconciliation Optimization"
	)
