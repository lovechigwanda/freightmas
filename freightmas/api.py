## Freightmas API Endpoints
###################################
import frappe
from erpnext.stock.utils import get_incoming_rate

@frappe.whitelist()
def get_fuel_rate(item_code, warehouse, posting_date=None):
    if not posting_date:
        posting_date = frappe.utils.today()

    args = {
        "item_code": item_code,
        "warehouse": warehouse,
        "posting_date": posting_date,
        "qty": 1,
        "allow_zero_valuation": 1
    }

    rate = get_incoming_rate(args)
    return rate or 0


################################################################################
import frappe
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from frappe.utils import now_datetime
import re

@frappe.whitelist()
def export_report_to_excel(report_name, filters=None):
    import json
    from io import BytesIO
    import importlib

    if isinstance(filters, str):
        filters = json.loads(filters)

    # Get columns and data using the report's execute method
    report = frappe.get_doc("Report", report_name)
    if report.report_type != "Script Report":
        frappe.throw("Only Script Reports are supported.")

    module = importlib.import_module(
        f"freightmas.{frappe.scrub(report.module)}.report.{frappe.scrub(report.name)}.{frappe.scrub(report.name)}"
    )
    columns, data = module.execute(filters)

    wb = openpyxl.Workbook()
    ws = wb.active

    sheet_title = re.sub(r'[\\/*?:\[\]]', '', report_name)[:31]
    ws.title = sheet_title

    # Styles
    bold_font = Font(bold=True, color="FFFFFF")
    title_font = Font(bold=True, size=16)
    subtitle_font = Font(bold=True, size=13)
    filter_label_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="305496")  # Modern blue
    zebra_fill = PatternFill("solid", fgColor="F2F2F2")  # Light gray for zebra
    border = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD')
    )
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    ncols = len(columns)
    row_idx = 1

    # Company Name (merged)
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=ncols)
    ws.cell(row=row_idx, column=1, value=frappe.defaults.get_user_default("Company")).font = title_font
    row_idx += 1

    # Report Title (merged)
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=ncols)
    ws.cell(row=row_idx, column=1, value=report_name).font = subtitle_font
    row_idx += 1

    # Filters (merged label and value)
    if filters:
        for label, val in filters.items():
            if val:
                # Format date filters
                if "date" in label and val:
                    try:
                        val = frappe.utils.formatdate(val, "dd-MMM-yy")
                    except Exception:
                        pass
                ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=1)
                ws.cell(row=row_idx, column=1, value=f"{label.replace('_', ' ').title()}:").font = filter_label_font
                ws.merge_cells(start_row=row_idx, start_column=2, end_row=row_idx, end_column=ncols)
                ws.cell(row=row_idx, column=2, value=val)
                row_idx += 1

    # Timestamp (label in first column, value in next column, merged across remaining columns)
    ws.merge_cells(start_row=row_idx, start_column=2, end_row=row_idx, end_column=ncols)
    ws.cell(row=row_idx, column=1, value="Exported:").font = filter_label_font
    ws.cell(row=row_idx, column=1).alignment = left_align
    export_time = now_datetime().strftime("%d-%b-%Y %H:%M")
    ws.cell(row=row_idx, column=2, value=export_time)
    ws.cell(row_idx, column=2).alignment = left_align
    row_idx += 1

    # Table Header
    header_row = row_idx
    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=col["label"])
        cell.font = bold_font
        cell.alignment = left_align
        cell.fill = header_fill
        cell.border = border
    row_idx += 1

    # Freeze panes below the header row
    ws.freeze_panes = ws[f"A{header_row+1}"]

    # Table Data (zebra striping)
    for i, row in enumerate(data, start=1):
        fill = zebra_fill if i % 2 == 0 else None
        for col_idx, col in enumerate(columns, start=1):
            value = row.get(col["fieldname"], "")
            cell = ws.cell(row=row_idx, column=col_idx)
            
            # Format numbers and currency
            if col.get("fieldtype") in ["Int", "Float", "Currency"]:
                if isinstance(value, (int, float)):
                    cell.value = value
                    cell.number_format = '#,##0.00'
                else:
                    cell.value = 0
                    cell.number_format = '#,##0.00'
            # Format dates
            elif "date" in col["fieldname"] and value:
                try:
                    cell.value = frappe.utils.formatdate(value, "dd-MMM-yy")
                except Exception:
                    cell.value = value
            else:
                cell.value = value
                
            cell.border = border
            if fill:
                cell.fill = fill
            # Alignment
            if col.get("fieldtype") in ["Int", "Float", "Currency"]:
                cell.alignment = right_align
            else:
                cell.alignment = left_align
        row_idx += 1

    # Auto-fit columns using only header and data rows
    for col_idx, col in enumerate(columns, start=1):
        max_length = 0
        # Only check header and data rows
        for row in ws.iter_rows(min_row=header_row, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
            for cell in row:
                try:
                    cell_length = len(str(cell.value)) if cell.value else 0
                    if cell_length > max_length:
                        max_length = cell_length
                except:
                    pass
        ws.column_dimensions[get_column_letter(col_idx)].width = max(12, min(max_length + 2, 40))

    # Hide gridlines
    ws.sheet_view.showGridLines = False

    # Save to BytesIO and return as file
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.local.response.filename = f"{report_name.replace(' ', '_')}.xlsx"
    frappe.local.response.filecontent = output.read()
    frappe.local.response.type = "binary"



###################################################
# Freightmas PDF Export for Script Reports
# This module exports Script Reports to PDF format.
# It uses Jinja templates for rendering the report
import frappe
import importlib
from frappe.utils.pdf import get_pdf
from frappe.utils.jinja import render_template
from frappe.utils import now_datetime
from frappe import _

@frappe.whitelist()
def export_report_to_pdf(report_name, filters):
    import json
    filters = json.loads(filters)

    # Dynamically import the report module and call its execute function
    report = frappe.get_doc("Report", report_name)
    if report.report_type != "Script Report":
        frappe.throw("Only Script Reports are supported.")

    module = importlib.import_module(
        f"freightmas.{frappe.scrub(report.module)}.report.{frappe.scrub(report.name)}.{frappe.scrub(report.name)}"
    )
    columns, data = module.execute(filters)

    # Format filter dates
    def format_date(val):
        if not val:
            return ""
        try:
            return frappe.utils.formatdate(val, "dd-MMM-yy")
        except Exception:
            return val

    formatted_filters = {}
    for k, v in filters.items():
        if "date" in k and v:
            formatted_filters[k] = format_date(v)
        else:
            formatted_filters[k] = v

    context = {
        "company": frappe.defaults.get_user_default("Company"),
        "title": _(report_name),
        "filters": formatted_filters,
        "columns": columns,
        "data": data,
        "frappe": frappe,
        "exported_at": frappe.utils.now_datetime().strftime("%d-%b-%Y %H:%M"),
    }

    html = frappe.render_template(
        "freightmas/templates/report_pdf_template.html", context
    )

    pdf = frappe.utils.pdf.get_pdf(
        html,
        options={
            "orientation": "Landscape",
            "footer-right": "Page [page] of [topage]",
            "footer-font-size": "10",
        }
    )

    frappe.local.response.filename = f"{report_name.replace(' ', '_')}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"

