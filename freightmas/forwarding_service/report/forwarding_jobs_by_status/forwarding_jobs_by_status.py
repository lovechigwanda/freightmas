# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, getdate


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {"label": "Category", "fieldname": "Category", "fieldtype": "Data", "width": 160},
        {"label": "Job Count", "fieldname": "Job Count", "fieldtype": "Int", "width": 120},
    ]


def get_data():
    current_year = getdate(today()).year

    # Jobs by Direction
    direction_rows = frappe.db.sql("""
        SELECT
            direction AS category,
            COUNT(*) AS job_count
        FROM `tabForwarding Job`
        WHERE docstatus < 2
          AND status != 'Cancelled'
          AND YEAR(date_created) = %s
          AND direction IS NOT NULL AND direction != ''
        GROUP BY direction
        ORDER BY job_count DESC
    """, (current_year,), as_dict=True)

    # Jobs by Mode
    mode_rows = frappe.db.sql("""
        SELECT
            shipment_mode AS category,
            COUNT(*) AS job_count
        FROM `tabForwarding Job`
        WHERE docstatus < 2
          AND status != 'Cancelled'
          AND YEAR(date_created) = %s
          AND shipment_mode IS NOT NULL AND shipment_mode != ''
        GROUP BY shipment_mode
        ORDER BY job_count DESC
    """, (current_year,), as_dict=True)

    data = []

    for row in direction_rows:
        data.append({
            "Category": row.category,
            "Job Count": row.job_count,
        })

    # Add a separator row
    if direction_rows and mode_rows:
        data.append({
            "Category": "--- By Mode ---",
            "Job Count": 0,
        })

    for row in mode_rows:
        data.append({
            "Category": row.category,
            "Job Count": row.job_count,
        })

    return data
