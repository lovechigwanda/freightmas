# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Get customers with active jobs (no date filtering)
    customers_with_jobs = frappe.db.sql(f"""
        SELECT customer, 
               COUNT(*) as total_jobs,
               MAX(modified) as last_update
        FROM `tabForwarding Job`
        WHERE status IN ('Draft', 'In Progress', 'Delivered')
              AND docstatus IN (0, 1)
        GROUP BY customer
        HAVING COUNT(*) > 0
        ORDER BY total_jobs DESC, last_update DESC
    """, as_dict=True)

    for customer_data in customers_with_jobs:
        # Get customer name
        customer_name = customer_data.get("customer", "")
        
        # Get required data
        total_jobs = customer_data.get("total_jobs", 0)
        last_update = format_date(customer_data.get("last_update"))
        
        data.append({
            "customer": customer_name,
            "total_jobs": total_jobs,
            "last_update": last_update
        })

    return columns, data

def get_columns():
    return [
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 800},
        {"label": "Total Jobs", "fieldname": "total_jobs", "fieldtype": "Int", "width": 120},
        {"label": "Last Update", "fieldname": "last_update", "fieldtype": "Data", "width": 150}
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