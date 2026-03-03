# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Shared export utilities for management account reports.
Provides nicely formatted Excel and PDF exports.
"""

import frappe
from frappe import _
from frappe.utils import flt, formatdate, now_datetime
import io
import re


# ----------------------------------------
# Columns to drop from exports
# ----------------------------------------

# These columns are dropped from BOTH Excel and PDF
ALWAYS_DROP = ["account", "party", "party_type", "voucher_type"]

# Additional columns dropped only from PDF (for page width)
PDF_EXTRA_DROP = ["remarks"]


def strip_html(text):
    """Remove HTML tags from text."""
    if not text:
        return text or ""
    return re.sub(r"<[^>]+>", "", str(text))


# ============================================================
# EXCEL EXPORT
# ============================================================

def build_excel_file(filters, data, columns, report_title, net_field_label="Net Amount"):
    """
    Build a formatted Excel workbook and return it as bytes.

    Args:
        filters: report filters dict
        data: list of row dicts from the report
        columns: list of column dicts from the report
        report_title: e.g. "Revenue Detail Report"
        net_field_label: label for the net amount column header
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = report_title[:31]  # Excel limit

    # ---- Styles ----
    title_font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    subtitle_font = Font(name="Calibri", size=10, color="555555")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    subtotal_font = Font(name="Calibri", size=10, bold=True, color="1F4E79")
    subtotal_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
    grand_total_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    grand_total_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    data_font = Font(name="Calibri", size=10)
    alt_row_fill = PatternFill(start_color="F2F7FB", end_color="F2F7FB", fill_type="solid")
    thin_border = Border(
        bottom=Side(style="thin", color="D9D9D9")
    )
    header_border = Border(
        bottom=Side(style="medium", color="1F4E79")
    )

    # ---- Filter columns for Excel (drop Account, Party, Party Type, Voucher Type) ----
    excel_columns = [c for c in columns if c.get("fieldname") not in ALWAYS_DROP]

    # ---- Header section ----
    company = filters.get("company", "")
    from_date = formatdate(filters.get("from_date"), "dd MMM yyyy") if filters.get("from_date") else ""
    to_date = formatdate(filters.get("to_date"), "dd MMM yyyy") if filters.get("to_date") else ""
    cost_center = filters.get("cost_center", "")

    row = 1
    num_cols = len(excel_columns)

    # Company name
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_cols)
    cell = ws.cell(row=row, column=1, value=company)
    cell.font = title_font
    cell.alignment = Alignment(horizontal="center")
    row += 1

    # Report title
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_cols)
    cell = ws.cell(row=row, column=1, value=report_title)
    cell.font = Font(name="Calibri", size=12, bold=True, color="333333")
    cell.alignment = Alignment(horizontal="center")
    row += 1

    # Date range
    date_text = f"Period: {from_date} to {to_date}"
    if cost_center:
        date_text += f"  |  Cost Center: {cost_center}"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_cols)
    cell = ws.cell(row=row, column=1, value=date_text)
    cell.font = subtitle_font
    cell.alignment = Alignment(horizontal="center")
    row += 1

    # Generated timestamp
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_cols)
    cell = ws.cell(row=row, column=1, value=f"Generated: {now_datetime().strftime('%d %b %Y %H:%M')}")
    cell.font = Font(name="Calibri", size=8, italic=True, color="999999")
    cell.alignment = Alignment(horizontal="center")
    row += 2  # blank row

    # ---- Column headers ----
    header_row = row
    for col_idx, col_def in enumerate(excel_columns, 1):
        cell = ws.cell(row=row, column=col_idx, value=strip_html(col_def.get("label", "")))
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = header_border
    row += 1

    # ---- Data rows ----
    currency_fields = set()
    for col_def in excel_columns:
        if col_def.get("fieldtype") == "Currency":
            currency_fields.add(col_def["fieldname"])

    data_start_row = row
    alt = False

    for row_data in data:
        if not row_data:
            # Blank separator — skip but keep alternating
            row += 1
            alt = False
            continue

        is_total = row_data.get("is_group_total", 0)
        is_grand = is_total and "Grand Total" in str(row_data.get("account_name", ""))

        for col_idx, col_def in enumerate(excel_columns, 1):
            fieldname = col_def["fieldname"]
            value = row_data.get(fieldname, "")

            # Strip HTML from text values
            if isinstance(value, str):
                value = strip_html(value)

            cell = ws.cell(row=row, column=col_idx, value=value)

            # Formatting
            if fieldname in currency_fields and value:
                cell.number_format = '#,##0.00'

            if col_def.get("fieldtype") == "Date" and value:
                cell.number_format = 'DD MMM YYYY'

            if is_grand:
                cell.font = grand_total_font
                cell.fill = grand_total_fill
                cell.alignment = Alignment(horizontal="right" if fieldname in currency_fields else "left")
            elif is_total:
                cell.font = subtotal_font
                cell.fill = subtotal_fill
                cell.alignment = Alignment(horizontal="right" if fieldname in currency_fields else "left")
            else:
                cell.font = data_font
                if alt:
                    cell.fill = alt_row_fill
                cell.border = thin_border
                if fieldname in currency_fields:
                    cell.alignment = Alignment(horizontal="right")

        if not is_total:
            alt = not alt
        row += 1

    # ---- Column widths ----
    col_widths = {
        "posting_date": 14,
        "account_name": 30,
        "cost_center": 22,
        "voucher_no": 22,
        "debit": 16,
        "credit": 16,
        "net_revenue": 18,
        "net_cost": 18,
        "net_expense": 18,
        "remarks": 35,
    }

    for col_idx, col_def in enumerate(excel_columns, 1):
        width = col_widths.get(col_def["fieldname"], 15)
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # ---- Freeze panes (freeze header row) ----
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

    # ---- Print setup ----
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.paperSize = ws.PAPERSIZE_A4

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


# ============================================================
# PDF EXPORT
# ============================================================

def build_pdf_file(filters, data, columns, report_title, net_fieldname="net_revenue"):
    """
    Build a formatted PDF and return it as bytes.

    Args:
        filters: report filters dict
        data: list of row dicts
        columns: list of column dicts
        report_title: e.g. "Revenue Detail Report"
        net_fieldname: the fieldname for the net amount column
    """
    from frappe.utils.pdf import get_pdf

    # Filter columns for PDF (drop more columns for page width)
    pdf_drop = set(ALWAYS_DROP + PDF_EXTRA_DROP)
    pdf_columns = [c for c in columns if c.get("fieldname") not in pdf_drop]

    company = filters.get("company", "")
    from_date = formatdate(filters.get("from_date"), "dd MMM yyyy") if filters.get("from_date") else ""
    to_date = formatdate(filters.get("to_date"), "dd MMM yyyy") if filters.get("to_date") else ""
    cost_center = filters.get("cost_center", "")
    generated = now_datetime().strftime("%d %b %Y %H:%M")

    currency_fields = set()
    for col_def in pdf_columns:
        if col_def.get("fieldtype") == "Currency":
            currency_fields.add(col_def["fieldname"])

    # Build HTML
    html = f"""
    <style>
        @page {{
            size: A4 landscape;
            margin: 12mm 10mm 12mm 10mm;
        }}
        body {{
            font-family: Calibri, Arial, sans-serif;
            font-size: 9pt;
            color: #333;
        }}
        .report-header {{
            text-align: center;
            margin-bottom: 10px;
        }}
        .company-name {{
            font-size: 16pt;
            font-weight: bold;
            color: #1F4E79;
            margin: 0;
        }}
        .report-title {{
            font-size: 12pt;
            font-weight: bold;
            color: #333;
            margin: 2px 0;
        }}
        .report-meta {{
            font-size: 9pt;
            color: #777;
            margin: 2px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
        }}
        th {{
            background-color: #1F4E79;
            color: white;
            font-weight: bold;
            font-size: 8.5pt;
            padding: 6px 5px;
            text-align: left;
            border-bottom: 2px solid #1F4E79;
        }}
        th.num {{
            text-align: right;
        }}
        td {{
            padding: 4px 5px;
            font-size: 8.5pt;
            border-bottom: 1px solid #e0e0e0;
        }}
        td.num {{
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        tr.alt {{
            background-color: #f7f9fc;
        }}
        tr.subtotal td {{
            font-weight: bold;
            color: #1F4E79;
            background-color: #D6E4F0;
            border-bottom: 1px solid #b0c4de;
        }}
        tr.grand-total td {{
            font-weight: bold;
            color: white;
            background-color: #1F4E79;
            font-size: 9pt;
        }}
        tr.separator td {{
            border: none;
            height: 6px;
        }}
        .footer {{
            text-align: center;
            font-size: 7pt;
            color: #aaa;
            margin-top: 10px;
        }}
    </style>

    <div class="report-header">
        <p class="company-name">{company}</p>
        <p class="report-title">{report_title}</p>
        <p class="report-meta">Period: {from_date} to {to_date}"""

    if cost_center:
        html += f"  |  Cost Center: {cost_center}"

    html += f"""</p>
    </div>

    <table>
        <thead>
            <tr>"""

    for col_def in pdf_columns:
        cls = ' class="num"' if col_def["fieldname"] in currency_fields else ""
        html += f'\n                <th{cls}>{strip_html(col_def.get("label", ""))}</th>'

    html += """
            </tr>
        </thead>
        <tbody>"""

    alt = False
    for row_data in data:
        if not row_data:
            html += '\n            <tr class="separator"><td colspan="{}">&nbsp;</td></tr>'.format(len(pdf_columns))
            alt = False
            continue

        is_total = row_data.get("is_group_total", 0)
        is_grand = is_total and "Grand Total" in str(row_data.get("account_name", ""))

        if is_grand:
            row_class = "grand-total"
        elif is_total:
            row_class = "subtotal"
        elif alt:
            row_class = "alt"
        else:
            row_class = ""

        html += f'\n            <tr class="{row_class}">'

        for col_def in pdf_columns:
            fieldname = col_def["fieldname"]
            value = row_data.get(fieldname, "")

            if isinstance(value, str):
                value = strip_html(value)

            if fieldname in currency_fields and value:
                try:
                    value = "{:,.2f}".format(flt(value))
                except (ValueError, TypeError):
                    pass
                html += f'\n                <td class="num">{value}</td>'
            elif col_def.get("fieldtype") == "Date" and value:
                try:
                    value = formatdate(value, "dd MMM yyyy")
                except Exception:
                    pass
                html += f"\n                <td>{value}</td>"
            else:
                html += f"\n                <td>{value}</td>"

        html += "\n            </tr>"

        if not is_total:
            alt = not alt

    html += """
        </tbody>
    </table>
    <div class="footer">
        Generated: {generated} | {report_title} | {company}
    </div>
    """.format(generated=generated, report_title=report_title, company=company)

    pdf_options = {
        "orientation": "Landscape",
        "page-size": "A4",
        "margin-top": "12mm",
        "margin-bottom": "12mm",
        "margin-left": "10mm",
        "margin-right": "10mm",
        "encoding": "UTF-8",
        "no-outline": None,
    }

    return get_pdf(html, options=pdf_options)


# ============================================================
# Frappe File Response Helpers
# ============================================================

def send_excel_response(file_bytes, filename):
    """Send Excel file as a download response."""
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = file_bytes
    frappe.local.response.type = "download"
    frappe.local.response.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def send_pdf_response(file_bytes, filename):
    """Send PDF file as a download response."""
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = file_bytes
    frappe.local.response.type = "download"
    frappe.local.response.content_type = "application/pdf"
