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

    Uses the same visual style as the shared ``export_report_to_excel``
    endpoint in ``freightmas.api`` so that all reports look uniform.

    Args:
        filters: report filters dict
        data: list of row dicts from the report
        columns: list of column dicts from the report
        report_title: e.g. "Revenue Detail Report"
        net_field_label: label for the net amount column header
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active

    sheet_title = re.sub(r'[\\/*?:\[\]]', '', report_title)[:31]
    ws.title = sheet_title

    # ---- Styles (matching api.py export_report_to_excel) ----
    title_font = Font(bold=True, size=16)
    subtitle_font = Font(bold=True, size=13)
    filter_label_font = Font(bold=True)
    bold_white_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="305496")
    zebra_fill = PatternFill("solid", fgColor="F2F2F2")
    subtotal_font = Font(bold=True, color="305496")
    subtotal_fill = PatternFill("solid", fgColor="D6DCE4")
    grand_total_font = Font(bold=True, color="FFFFFF")
    grand_total_fill = PatternFill("solid", fgColor="305496")
    border = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD'),
    )
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    # ---- Filter columns for Excel (drop Account, Party, Party Type, Voucher Type) ----
    excel_columns = [c for c in columns if c.get("fieldname") not in ALWAYS_DROP]
    ncols = len(excel_columns)

    row_idx = 1

    # ---- Company Name (merged) ----
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=ncols)
    ws.cell(row=row_idx, column=1, value=filters.get("company", "")).font = title_font
    row_idx += 1

    # ---- Report Title (merged) ----
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=ncols)
    ws.cell(row=row_idx, column=1, value=report_title).font = subtitle_font
    row_idx += 1

    # ---- Filters as label : value rows ----
    display_filters = {
        "from_date": "From Date",
        "to_date": "To Date",
        "fiscal_year": "Fiscal Year",
        "cost_center": "Cost Center",
        "account": "Account",
        "party_type": "Party Type",
        "party": "Party",
        "voucher_type": "Voucher Type",
        "group_by": "Group By",
    }
    for key, label in display_filters.items():
        val = filters.get(key)
        if val:
            # Format date values
            if "date" in key:
                try:
                    val = formatdate(val, "dd-MMM-yy")
                except Exception:
                    pass
            ws.cell(row=row_idx, column=1, value=f"{label}:").font = filter_label_font
            ws.merge_cells(start_row=row_idx, start_column=2, end_row=row_idx, end_column=ncols)
            ws.cell(row=row_idx, column=2, value=val)
            row_idx += 1

    # ---- Exported timestamp ----
    ws.cell(row=row_idx, column=1, value="Exported:").font = filter_label_font
    ws.cell(row=row_idx, column=1).alignment = left_align
    ws.merge_cells(start_row=row_idx, start_column=2, end_row=row_idx, end_column=ncols)
    export_time = now_datetime().strftime("%d-%b-%Y %H:%M")
    ws.cell(row=row_idx, column=2, value=export_time).alignment = left_align
    row_idx += 1

    # ---- Column headers ----
    header_row = row_idx
    for col_idx, col_def in enumerate(excel_columns, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=strip_html(col_def.get("label", "")))
        cell.font = bold_white_font
        cell.alignment = left_align
        cell.fill = header_fill
        cell.border = border
    row_idx += 1

    # ---- Freeze panes below header ----
    ws.freeze_panes = ws[f"A{header_row + 1}"]

    # ---- Identify currency fields ----
    currency_fields = set()
    for col_def in excel_columns:
        if col_def.get("fieldtype") == "Currency":
            currency_fields.add(col_def["fieldname"])

    # ---- Data rows (zebra striping, subtotals, grand total) ----
    data_row_num = 0

    for row_data in data:
        if not row_data:
            # Blank separator row
            row_idx += 1
            data_row_num = 0
            continue

        is_total = row_data.get("is_group_total", 0)
        is_grand = is_total and "Grand Total" in str(row_data.get("account_name", ""))

        data_row_num += 1

        for col_idx, col_def in enumerate(excel_columns, 1):
            fieldname = col_def["fieldname"]
            value = row_data.get(fieldname, "")

            # Strip HTML from text values
            if isinstance(value, str):
                value = strip_html(value)

            cell = ws.cell(row=row_idx, column=col_idx)

            # Format numbers and currency
            if col_def.get("fieldtype") in ("Int", "Float", "Currency"):
                if isinstance(value, (int, float)):
                    cell.value = value
                    cell.number_format = '#,##0.00'
                else:
                    cell.value = 0
                    cell.number_format = '#,##0.00'
            elif "date" in fieldname and value:
                try:
                    cell.value = formatdate(value, "dd-MMM-yy")
                except Exception:
                    cell.value = value
            else:
                cell.value = value

            cell.border = border

            # Row-level styling
            if is_grand:
                cell.font = grand_total_font
                cell.fill = grand_total_fill
                cell.alignment = right_align if fieldname in currency_fields else left_align
            elif is_total:
                cell.font = subtotal_font
                cell.fill = subtotal_fill
                cell.alignment = right_align if fieldname in currency_fields else left_align
            else:
                # Zebra striping
                if data_row_num % 2 == 0:
                    cell.fill = zebra_fill
                # Alignment
                cell.alignment = right_align if col_def.get("fieldtype") in ("Int", "Float", "Currency") else left_align

        if is_total:
            data_row_num = 0

        row_idx += 1

    # ---- Auto-fit column widths (matching api.py approach) ----
    for col_idx in range(1, ncols + 1):
        max_length = 0
        for row in ws.iter_rows(min_row=header_row, max_row=ws.max_row,
                                min_col=col_idx, max_col=col_idx):
            for cell in row:
                try:
                    cell_length = len(str(cell.value)) if cell.value else 0
                    if cell_length > max_length:
                        max_length = cell_length
                except Exception:
                    pass
        ws.column_dimensions[get_column_letter(col_idx)].width = max(12, min(max_length + 2, 40))

    # ---- Hide gridlines ----
    ws.sheet_view.showGridLines = False

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
