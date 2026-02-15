# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
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
        {"label": "Actual Margin", "fieldname": "Actual Margin", "fieldtype": "Currency", "width": 160},
    ]


def get_data():
    current = today()

    # Build month buckets for last 12 months
    months = []
    for i in range(11, -1, -1):
        month_date = add_months(current, -i)
        start_date = get_first_day(month_date)
        end_date = get_last_day(month_date)
        month_label = formatdate(start_date, "MMM YYYY")
        months.append({
            "label": month_label,
            "start": start_date,
            "end": end_date,
        })

    # Planned margin: SUM(total_quoted_profit_base) grouped by month of COALESCE(eta, date_created)
    planned_rows = frappe.db.sql("""
        SELECT
            DATE_FORMAT(COALESCE(eta, date_created), '%%Y-%%m') AS month_key,
            COALESCE(SUM(total_quoted_profit_base), 0) AS planned_margin
        FROM `tabForwarding Job`
        WHERE docstatus < 2
          AND status != 'Cancelled'
          AND COALESCE(eta, date_created) BETWEEN %s AND %s
        GROUP BY month_key
    """, (months[0]["start"], months[-1]["end"]), as_dict=True)

    planned_map = {row.month_key: row.planned_margin for row in planned_rows}

    # Actual margin: SI.base_grand_total - PI.base_grand_total for submitted jobs
    # grouped by month of revenue_recognised_on
    actual_rows = frappe.db.sql("""
        SELECT
            DATE_FORMAT(fj.revenue_recognised_on, '%%Y-%%m') AS month_key,
            SUM(COALESCE(si_agg.total_si, 0)) - SUM(COALESCE(pi_agg.total_pi, 0)) AS actual_margin
        FROM `tabForwarding Job` fj
        LEFT JOIN (
            SELECT forwarding_job_reference, SUM(base_grand_total) AS total_si
            FROM `tabSales Invoice`
            WHERE docstatus = 1 AND is_forwarding_invoice = 1
            GROUP BY forwarding_job_reference
        ) si_agg ON si_agg.forwarding_job_reference = fj.name
        LEFT JOIN (
            SELECT forwarding_job_reference, SUM(base_grand_total) AS total_pi
            FROM `tabPurchase Invoice`
            WHERE docstatus = 1 AND is_forwarding_invoice = 1
            GROUP BY forwarding_job_reference
        ) pi_agg ON pi_agg.forwarding_job_reference = fj.name
        WHERE fj.docstatus = 1
          AND fj.revenue_recognised_on IS NOT NULL
          AND fj.revenue_recognised_on BETWEEN %s AND %s
        GROUP BY month_key
    """, (months[0]["start"], months[-1]["end"]), as_dict=True)

    actual_map = {row.month_key: row.actual_margin for row in actual_rows}

    # Merge into output
    data = []
    for m in months:
        month_key = m["start"].strftime("%Y-%m") if hasattr(m["start"], "strftime") else str(m["start"])[:7]
        data.append({
            "Month": m["label"],
            "Planned Margin": planned_map.get(month_key, 0),
            "Actual Margin": actual_map.get(month_key, 0),
        })

    return data
