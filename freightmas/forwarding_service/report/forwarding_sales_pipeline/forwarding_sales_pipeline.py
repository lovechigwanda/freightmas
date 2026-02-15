# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, add_months, get_first_day, get_last_day, formatdate


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {"label": "Month", "fieldname": "Month", "fieldtype": "Data", "width": 120},
        {"label": "Planned Margin", "fieldname": "Planned Margin", "fieldtype": "Currency", "width": 160},
    ]


def get_data():
    data = []
    current = today()

    for i in range(11, -1, -1):
        month_date = add_months(current, -i)
        start_date = get_first_day(month_date)
        end_date = get_last_day(month_date)
        month_label = formatdate(start_date, "MMM YYYY")

        result = frappe.db.sql("""
            SELECT COALESCE(SUM(total_quoted_profit_base), 0) AS planned_margin
            FROM `tabForwarding Job`
            WHERE docstatus < 2
              AND status != 'Cancelled'
              AND date_created BETWEEN %s AND %s
        """, (start_date, end_date), as_dict=True)[0]

        data.append({
            "Month": month_label,
            "Planned Margin": result.planned_margin,
        })

    return data
