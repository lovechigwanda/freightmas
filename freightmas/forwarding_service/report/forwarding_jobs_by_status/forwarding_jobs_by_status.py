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
        {"label": "Status", "fieldname": "Status", "fieldtype": "Data", "width": 150},
        {"label": "Job Count", "fieldname": "Job Count", "fieldtype": "Int", "width": 120},
    ]


def get_data():
    start_date = get_first_day(today())
    end_date = get_last_day(today())

    results = frappe.db.sql("""
        SELECT status, COUNT(*) AS job_count
        FROM `tabForwarding Job`
        WHERE docstatus < 2
        AND status != 'Cancelled'
        AND date_created BETWEEN %s AND %s
        GROUP BY status
        ORDER BY FIELD(status, 'Draft', 'In Progress', 'Delivered', 'Completed', 'Closed')
    """, (start_date, end_date), as_dict=True)

    data = []
    for row in results:
        data.append({
            "Status": row.status,
            "Job Count": row.job_count,
        })

    return data
