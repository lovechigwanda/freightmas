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
## Download Job Milestone Tracker Imports Excel
import frappe
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from io import BytesIO
from datetime import datetime

@frappe.whitelist()
def download_job_milestone_excel(filters=None):
    from freightmas.clearing_service.report.job_milestone_tracker_imports import job_milestone_tracker_imports

    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    columns, data = job_milestone_tracker_imports.execute(filters)

    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Milestone Tracker Imports"

    # Styling for header
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    alignment = Alignment(horizontal="center", vertical="center")

    # Write headers
    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col["label"])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = alignment

    # Write data rows
    for row_idx, row in enumerate(data, start=2):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-adjust column widths
    for col_idx in range(1, len(columns) + 1):
        col_letter = get_column_letter(col_idx)
        max_length = max(
            (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, len(data) + 2)),
            default=0
        )
        ws.column_dimensions[col_letter].width = max_length + 2

    # Robust date formatting for filename
    def fmt(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%b-%Y") if date_str else "All"
        except Exception:
            return "All"

    from_date = fmt(filters.get("from_date"))
    to_date = fmt(filters.get("to_date"))
    filename = f"Job_Milestone_Tracker_Imports_{from_date}_to_{to_date}.xlsx"

    # Return as binary file using Frappe's response object
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = output.read()
    frappe.local.response.type = "binary"


    #################################################################
## Download Container Tracker Excel
@frappe.whitelist()
def download_container_tracker_excel(filters=None):
    from freightmas.clearing_service.report.container_tracker import container_tracker
    from io import BytesIO
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    from datetime import datetime

    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    columns, data = container_tracker.execute(filters)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Container Tracker"

    # Header styling
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    align_center = Alignment(horizontal="center", vertical="center")

    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col["label"])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center

    for row_idx, row in enumerate(data, start=2):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    for col_idx in range(1, len(columns) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = max((len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, len(data) + 2)), default=0)
        ws.column_dimensions[col_letter].width = max_len + 2

    def fmt(d):
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b-%Y") if d else "All"

    from_date = fmt(filters.get("from_date"))
    to_date = fmt(filters.get("to_date"))
    filename = f"Container_Tracker_{from_date}_to_{to_date}.xlsx"

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = output.read()
    frappe.local.response.type = "binary"


##################################################################
## Download Container Status Excel
@frappe.whitelist()
def download_container_status_excel(filters=None):
    from freightmas.clearing_service.report.container_status_tracker import container_status_tracker
    from io import BytesIO
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    from datetime import datetime

    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    columns, data = container_status_tracker.execute(filters)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Container Status"

    # Styles
    title_font = Font(bold=True, size=14)
    label_font = Font(bold=True)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="305496")  # dark blue
    align_left = Alignment(horizontal="left")
    align_center = Alignment(horizontal="center")

    # === Report Title ===
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
    ws.cell(row=1, column=1, value="Container Status Tracker").font = title_font

    # === Filter Info ===
    filter_row = 3
    filter_map = {
        "From Date": filters.get("from_date"),
        "To Date": filters.get("to_date"),
        "Client": filters.get("customer"),
        "Job No": filters.get("job_no"),
        "BL No": filters.get("bl_number"),
        "Report Type": filters.get("report_type")
    }

    def fmt_date(d):  # use dd-mmm-yy for consistency
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b-%y") if d else "All"
        except Exception:
            return d or "All"

    for idx, (label, value) in enumerate(filter_map.items(), start=0):
        ws.cell(row=filter_row + idx, column=1, value=label).font = label_font
        if "Date" in label:
            ws.cell(row=filter_row + idx, column=2, value=fmt_date(value))
        else:
            ws.cell(row=filter_row + idx, column=2, value=value or "All")

    # === Table Headers ===
    header_row = filter_row + len(filter_map) + 2
    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=col["label"])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center

    # === Data ===
    for row_idx, row in enumerate(data, start=header_row + 1):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # === Auto Column Widths ===
    for col_idx in range(1, len(columns) + 1):
        col_letter = get_column_letter(col_idx)
        max_length = max(
            (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, ws.max_row + 1)),
            default=0
        )
        ws.column_dimensions[col_letter].width = max_length + 2

    # === Filename ===
    filename = f"Container_Status_Tracker_{fmt_date(filters.get('from_date'))}_to_{fmt_date(filters.get('to_date'))}.xlsx"

    # === Return as Download ===
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = output.read()
    frappe.local.response.type = "binary"


#################################################################################
### Download Container Status PDF
@frappe.whitelist()
def download_container_status_pdf(filters=None):
    from freightmas.clearing_service.report.container_status_tracker import container_status_tracker
    from frappe.utils.pdf import get_pdf
    from frappe import render_template
    from datetime import datetime

    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    columns, data = container_status_tracker.execute(filters)

    user = frappe.session.user
    company = frappe.defaults.get_user_default("Company")
    printed_on = datetime.now().strftime("%d-%b-%Y %H:%M")

    report_name = "Container Status Tracker"
    filter_map = {
        "From Date": filters.get("from_date"),
        "To Date": filters.get("to_date"),
        "Client": filters.get("customer"),
        "Job No": filters.get("job_no"),
        "BL No": filters.get("bl_number"),
        "Report Type": filters.get("report_type")
    }

    def fmt_date(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b-%y") if d else "All"
        except Exception:
            return d or "All"

    # Format filter dates for PDF heading
    filter_map["From Date"] = fmt_date(filter_map.get("From Date"))
    filter_map["To Date"] = fmt_date(filter_map.get("To Date"))

    context = {
        "company": company,
        "report_name": report_name,
        "filters": filter_map,
        "columns": [col["label"] for col in columns],
        "data": data,
        "printed_by": user,
        "printed_on": printed_on
    }

    html = render_template("freightmas/templates/container_status_pdf.html", context)
    pdf = get_pdf(html, {"orientation": "Landscape"})

    filename = f"{report_name.replace(' ', '_')}_{filter_map['From Date']}_to_{filter_map['To Date']}.pdf"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"

#######################################################################
### Download Clearing Job Register Excel

import frappe
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment

@frappe.whitelist()
def download_clearing_job_register_excel(date_from=None, date_to=None, direction=None, status=None):
    from io import BytesIO
    from freightmas.clearing_service.report.clearing_job_register import clearing_job_register

    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "direction": direction,
        "status": status,
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v}

    columns, data = clearing_job_register.execute(filters=filters)

    wb = Workbook()
    ws = wb.active
    ws.title = "Clearing Job Register"

    # Header styling
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    alignment = Alignment(horizontal="center", vertical="center")

    # Write headers
    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col["label"])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = alignment
        ws.column_dimensions[get_column_letter(col_idx)].width = max(14, len(col["label"]) + 2)

    # Write data rows
    for row_idx, row in enumerate(data, start=2):
        # If data is dicts
        if isinstance(row, dict):
            for col_idx, col in enumerate(columns, start=1):
                ws.cell(row=row_idx, column=col_idx, value=row.get(col["fieldname"]))
        # If data is lists/tuples
        else:
            for col_idx, value in enumerate(row, start=1):
                ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-adjust column widths
    for col_idx in range(1, len(columns) + 1):
        col_letter = get_column_letter(col_idx)
        max_length = max(
            (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, ws.max_row + 1)),
            default=0
        )
        ws.column_dimensions[col_letter].width = max(14, max_length + 2)

    # Dynamic filename using date range
    from datetime import datetime
    def fmt(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%b-%Y") if date_str else "All"
        except Exception:
            return "All"

    from_date = fmt(filters.get("date_from"))
    to_date = fmt(filters.get("date_to"))
    filename = f"Clearing_Job_Register_{from_date}_to_{to_date}.xlsx"

    # Response
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = output.read()
    frappe.local.response.type = "binary"

##############################################################################
## Download Milestone Tracker Import Excel
import frappe
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from io import BytesIO
from datetime import datetime

@frappe.whitelist()
def download_milestone_tracker_import_excel(filters=None):
    from freightmas.clearing_service.report.milestone_tracker_import import milestone_tracker_import

    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    columns, data = milestone_tracker_import.execute(filters)

    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Milestone Tracker Import"

    # Styling for header
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    alignment = Alignment(horizontal="center", vertical="center")

    # Write headers
    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col["label"])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = alignment

    # Write data rows
    for row_idx, row in enumerate(data, start=2):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-adjust column widths
    for col_idx in range(1, len(columns) + 1):
        col_letter = get_column_letter(col_idx)
        max_length = max(
            (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, len(data) + 2)),
            default=0
        )
        ws.column_dimensions[col_letter].width = max_length + 2

    # Robust date formatting for filename
    def fmt(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%b-%Y") if date_str else "All"
        except Exception:
            return "All"

    from_date = fmt(filters.get("from_date"))
    to_date = fmt(filters.get("to_date"))
    filename = f"Milestone_Tracker_Import_{from_date}_to_{to_date}.xlsx"

    # Return as binary file using Frappe's response object
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = output.read()
    frappe.local.response.type = "binary"


    ###########################################################################
