# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, get_first_day, get_last_day


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {"label": "Customer", "fieldname": "Customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": "Working Revenue", "fieldname": "Working Revenue", "fieldtype": "Currency", "width": 160},
        {"label": "Invoiced Revenue", "fieldname": "Invoiced Revenue", "fieldtype": "Currency", "width": 160},
    ]


def get_data():
    start_date = get_first_day(today())
    end_date = get_last_day(today())

    working_revenue_data = frappe.db.sql("""
        SELECT customer, COALESCE(SUM(total_working_revenue_base), 0) AS total_amount
        FROM `tabForwarding Job`
        WHERE docstatus < 2
        AND status != 'Cancelled'
        AND date_created BETWEEN %s AND %s
        GROUP BY customer
    """, (start_date, end_date), as_dict=True)

    invoiced_revenue_data = frappe.db.sql("""
        SELECT
            fj.customer,
            COALESCE(SUM(si.grand_total), 0) AS total_amount
        FROM `tabForwarding Job` fj
        JOIN `tabSales Invoice` si ON si.forwarding_job_reference = fj.name
        WHERE si.docstatus = 1
        AND fj.date_created BETWEEN %s AND %s
        GROUP BY fj.customer
    """, (start_date, end_date), as_dict=True)

    working_revenue = {row["customer"]: row.get("total_amount", 0) for row in working_revenue_data}
    invoiced_revenue = {row["customer"]: row.get("total_amount", 0) for row in invoiced_revenue_data}

    customers = sorted(set(working_revenue.keys()) | set(invoiced_revenue.keys()))

    data = []
    for customer in customers:
        data.append({
            "Customer": customer,
            "Working Revenue": working_revenue.get(customer, 0),
            "Invoiced Revenue": invoiced_revenue.get(customer, 0),
        })

    return data
