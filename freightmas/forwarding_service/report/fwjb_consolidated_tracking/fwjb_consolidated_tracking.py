# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build date conditions
    date_conditions = "1=1"
    if filters.get("from_date"):
        date_conditions += f" AND date_created >= '{filters['from_date']}'"
    if filters.get("to_date"):
        date_conditions += f" AND date_created <= '{filters['to_date']}'"

    # Get customers with active jobs
    customers_with_jobs = frappe.db.sql(f"""
        SELECT customer, 
               COUNT(*) as total_jobs,
               SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
               SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered,
               SUM(CASE WHEN status = 'Draft' THEN 1 ELSE 0 END) as draft,
               SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
               MAX(modified) as last_update
        FROM `tabForwarding Job`
        WHERE {date_conditions} 
              AND status IN ('Draft', 'In Progress', 'Delivered')
              AND docstatus IN (0, 1)
        GROUP BY customer
        HAVING COUNT(*) > 0
        ORDER BY total_jobs DESC, last_update DESC
    """, as_dict=True)

    for customer_data in customers_with_jobs:
        # Get customer name
        customer_name = customer_data.get("customer", "")
        
        # Calculate summary metrics
        total_jobs = customer_data.get("total_jobs", 0)
        in_progress = customer_data.get("in_progress", 0)
        delivered = customer_data.get("delivered", 0)
        draft = customer_data.get("draft", 0)
        completed = customer_data.get("completed", 0)
        
        # Create status summary
        status_summary = []
        if draft > 0:
            status_summary.append(f"{draft} Draft")
        if in_progress > 0:
            status_summary.append(f"{in_progress} In Progress")
        if delivered > 0:
            status_summary.append(f"{delivered} Delivered")
        if completed > 0:
            status_summary.append(f"{completed} Completed")
        
        status_text = " | ".join(status_summary) if status_summary else "No Active Jobs"
        
        # Get latest job for priority indicator
        priority_indicator = "Normal"
        if in_progress > 0:
            priority_indicator = "Active"
        if delivered > 0:
            priority_indicator = "Pending Completion"
            
        data.append({
            "customer": customer_name,
            "total_jobs": total_jobs,
            "status_summary": status_text,
            "in_progress": in_progress,
            "delivered": delivered,
            "draft": draft,
            "completed": completed,
            "last_update": format_date(customer_data.get("last_update")),
            "priority": priority_indicator
        })

    return columns, data

def get_columns():
    return [
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Total Jobs", "fieldname": "total_jobs", "fieldtype": "Int", "width": 100},
        {"label": "Status Summary", "fieldname": "status_summary", "fieldtype": "Data", "width": 250},
        {"label": "In Progress", "fieldname": "in_progress", "fieldtype": "Int", "width": 90},
        {"label": "Delivered", "fieldname": "delivered", "fieldtype": "Int", "width": 90},
        {"label": "Draft", "fieldname": "draft", "fieldtype": "Int", "width": 70},
        {"label": "Completed", "fieldname": "completed", "fieldtype": "Int", "width": 90},
        {"label": "Last Update", "fieldname": "last_update", "fieldtype": "Data", "width": 100},
        {"label": "Priority", "fieldname": "priority", "fieldtype": "Data", "width": 120}
    ]

@frappe.whitelist()
def generate_customer_tracking_pdf(customer):
    """Generate consolidated tracking PDF using print format"""
    try:
        # Get the PDF using the print format
        pdf = frappe.get_print(
            doctype="Customer",
            name=customer,
            print_format="Customer Consolidated Tracking",
            as_pdf=True
        )
        
        # Create filename
        import base64
        timestamp = frappe.utils.now_datetime().strftime('%Y%m%d_%H%M')
        filename = f"Consolidated_Tracking_{customer}_{timestamp}.pdf"
        
        # Return base64 encoded PDF
        pdf_base64 = base64.b64encode(pdf).decode('utf-8')
        
        return {
            "pdf_content": pdf_base64,
            "filename": filename
        }
        
    except Exception as e:
        frappe.log_error(f"PDF Generation Error for {customer}: {str(e)}", "Customer Tracking PDF")
        frappe.throw(f"Error generating PDF: {str(e)}")

def format_date(date_value):
    """Format date string to dd-MMM-yy format."""
    if not date_value:
        return ""
    try:
        return formatdate(date_value, "dd-MMM-yy")
    except Exception:
        return str(date_value)