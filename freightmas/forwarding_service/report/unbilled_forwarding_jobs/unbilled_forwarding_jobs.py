import frappe
from freightmas.utils import report_utils
def execute(filters=None):
    from freightmas.utils.report_utils import (
        get_standard_columns,
        build_job_filters,
        process_job_data,
        validate_date_filters
    )

def get_columns():
    standard_cols = report_utils.get_standard_columns()
    columns = [
        standard_cols["job_id"],
        standard_cols["job_date"],
        standard_cols["customer"],
        standard_cols["reference"],
        standard_cols["direction"],
        standard_cols["status"],
        # Add custom columns as needed
        {"label": "Quoted Revenue", "fieldname": "quoted_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Quoted Cost", "fieldname": "quoted_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Quoted Profit", "fieldname": "quoted_profit", "fieldtype": "Currency", "width": 120},
        {"label": "Working Revenue", "fieldname": "working_revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Working Cost", "fieldname": "working_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Working Profit", "fieldname": "working_profit", "fieldtype": "Currency", "width": 120},
    ]
    return columns

def execute(filters=None):
    filters = report_utils.validate_date_filters(filters or {})
    columns = get_columns()
    job_filters = report_utils.build_job_filters(filters, "Forwarding Job")
    job_filters["status"] = ["!=", "Cancelled"]
    jobs = frappe.get_all(
        "Forwarding Job",
        filters=job_filters,
        fields=[
            "name", "date_created", "customer", "customer_reference", "direction", "status",
            "total_quoted_revenue_base", "total_quoted_cost_base", "total_quoted_profit_base",
            "total_working_revenue_base", "total_working_cost", "total_working_profit_base"
        ],
        order_by="date_created desc"
    )
    data = []
    for job in jobs:
        invoiced_revenue = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabSales Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference = %s
        """, (job["name"]))[0][0] or 0
        invoiced_cost = frappe.db.sql("""
            SELECT SUM(grand_total) FROM `tabPurchase Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference = %s
        """, (job["name"]))[0][0] or 0
        if invoiced_revenue == 0 or invoiced_cost == 0:
            row = {
                "job_id": job["name"],
                "job_date": job["date_created"],
                "customer": job["customer"],
                "customer_reference": job["customer_reference"],
                "direction": job["direction"],
                "status": job["status"],
                "quoted_revenue": job["total_quoted_revenue_base"],
                "quoted_cost": job["total_quoted_cost_base"],
                "quoted_profit": job["total_quoted_profit_base"],
                "working_revenue": job["total_working_revenue_base"],
                "working_cost": job["total_working_cost"],
                "working_profit": job["total_working_profit_base"],
            }
            data.append(row)
    data = report_utils.process_job_data(data, service_type="forwarding")
    return columns, data
