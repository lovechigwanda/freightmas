# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Shared Statement of Account (Job Linked) export helpers for Desk and Portal."""

from io import BytesIO

import frappe
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook

from freightmas.api import get_report_filename
from freightmas.utils.company_branding import company_logo_data_uri


def _report_module():
	return frappe.get_module(
		"freightmas.freightmas.report.statement_of_account_job_linked.statement_of_account_job_linked"
	)


def _format_display_date(date_str):
	if date_str:
		return frappe.utils.formatdate(date_str, "dd-MMM-yy")
	return ""


def _party_display_name(party_type, party):
	if not party:
		return None
	field = "customer_name" if party_type == "Customer" else "supplier_name"
	return frappe.db.get_value(party_type, party, field) or party


def _report_context(filters, data):
	party_type = filters.get("party_type")
	party = filters.get("party")
	total_debit = sum(row.get("debit", 0) for row in data if row.get("debit"))
	total_credit = sum(row.get("credit", 0) for row in data if row.get("credit"))
	closing_balance = data[-1].get("balance", 0) if data else 0
	company = filters.get("company")
	company_currency = frappe.db.get_value("Company", company, "default_currency") or "USD"
	company_name = frappe.db.get_value("Company", company, "company_name") or company
	statement_date = _format_display_date(frappe.utils.today())

	return {
		"company": company,
		"company_name": company_name,
		"logo": company_logo_data_uri(company),
		"party_type": party_type,
		"party_name": _party_display_name(party_type, party) or party,
		"report_name": "Statement of Account Job Linked",
		"from_date": _format_display_date(filters.get("from_date")),
		"to_date": _format_display_date(filters.get("to_date")),
		"statement_date": statement_date,
		"currency": company_currency,
		"include_draft": filters.get("include_draft_invoices", False),
		"data": data,
		"totals": {
			"debit": total_debit,
			"credit": total_credit,
			"balance": closing_balance,
		},
		"frappe": frappe,
		"today": frappe.utils.today(),
	}


def build_statement_job_linked_pdf(filters):
	_columns, data = _report_module().execute(filters)
	context = _report_context(filters, data)
	html = frappe.render_template("freightmas/templates/statement_of_account_job_linked.html", context)
	pdf = frappe.utils.pdf.get_pdf(
		html,
		{
			"orientation": "Landscape",
			"page-size": "A4",
			"margin-top": "10mm",
			"margin-right": "10mm",
			"margin-bottom": "14mm",
			"margin-left": "10mm",
			"footer-right": "Page [page] of [topage]",
			"footer-font-size": "8",
			"print-media-type": True,
		},
	)
	filename = get_report_filename("Statement_of_Account_Job_Linked", "pdf", filters.get("party"))
	return filename, pdf


def build_statement_job_linked_excel(filters):
	columns, data = _report_module().execute(filters)
	party_type = filters.get("party_type")
	party = filters.get("party")
	party_name = _party_display_name(party_type, party) or party

	wb = Workbook()
	ws = wb.active
	ws.title = "Statement"

	header_font = Font(bold=True, color="FFFFFF")
	title_font = Font(bold=True, size=14)
	subtitle_font = Font(bold=True, size=12)
	total_font = Font(bold=True)
	header_fill = PatternFill("solid", fgColor="305496")
	thin_border = Border(
		left=Side(style="thin"),
		right=Side(style="thin"),
		top=Side(style="thin"),
		bottom=Side(style="thin"),
	)

	current_row = 1
	num_cols = len(columns)
	last_col = get_column_letter(num_cols)

	ws.merge_cells(f"A{current_row}:{last_col}{current_row}")
	ws[f"A{current_row}"] = filters.get("company")
	ws[f"A{current_row}"].font = title_font
	current_row += 1

	ws.merge_cells(f"A{current_row}:{last_col}{current_row}")
	ws[f"A{current_row}"] = "Statement of Account Job Linked"
	ws[f"A{current_row}"].font = subtitle_font
	current_row += 1

	ws.merge_cells(f"A{current_row}:{last_col}{current_row}")
	ws[f"A{current_row}"] = f"{party_type}: {party_name}"
	ws[f"A{current_row}"].font = subtitle_font
	current_row += 1

	for col_idx, col in enumerate(columns, 1):
		cell = ws.cell(row=current_row, column=col_idx, value=col.get("label"))
		cell.font = header_font
		cell.fill = header_fill
		cell.border = thin_border

	current_row += 1

	for row in data:
		for col_idx, col in enumerate(columns, 1):
			field = col.get("fieldname")
			cell = ws.cell(row=current_row, column=col_idx, value=row.get(field))

			if col.get("fieldtype") in ["Currency", "Float"]:
				cell.number_format = "#,##0.00"
				cell.alignment = Alignment(horizontal="right")

			cell.border = thin_border

			if row.get("voucher_type") in ["Opening Balance", "Closing Balance"]:
				cell.font = total_font

		current_row += 1

	for col in range(1, num_cols + 1):
		ws.column_dimensions[get_column_letter(col)].width = 15

	output = BytesIO()
	wb.save(output)
	output.seek(0)
	filename = get_report_filename("Statement_of_Account_Job_Linked", "xlsx", party)
	return filename, output.read()
