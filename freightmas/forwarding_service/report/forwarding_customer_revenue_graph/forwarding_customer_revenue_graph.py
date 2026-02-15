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
        {"label": "Customer", "fieldname": "Customer", "fieldtype": "Link", "options": "Customer", "width": 220},
        {"label": "Closed Margin", "fieldname": "Closed Margin", "fieldtype": "Currency", "width": 160},
        {"label": "In Progress Margin", "fieldname": "In Progress Margin", "fieldtype": "Currency", "width": 160},
        {"label": "Total Margin", "fieldname": "Total Margin", "fieldtype": "Currency", "width": 160},
    ]


def get_data():
    current_year = getdate(today()).year

    # Closed margin per customer: actual invoiced margin (SI - PI) for submitted jobs
    closed_rows = frappe.db.sql("""
        SELECT
            fj.customer,
            SUM(COALESCE(si_agg.total_si, 0)) - SUM(COALESCE(pi_agg.total_pi, 0)) AS closed_margin
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
          AND YEAR(fj.date_created) = %s
        GROUP BY fj.customer
    """, (current_year,), as_dict=True)

    closed_map = {row.customer: row.closed_margin or 0 for row in closed_rows}

    # In progress margin per customer: planned margin for non-submitted active jobs
    progress_rows = frappe.db.sql("""
        SELECT
            customer,
            COALESCE(SUM(total_quoted_profit_base), 0) AS in_progress_margin
        FROM `tabForwarding Job`
        WHERE docstatus = 0
          AND status != 'Cancelled'
          AND YEAR(date_created) = %s
        GROUP BY customer
    """, (current_year,), as_dict=True)

    progress_map = {row.customer: row.in_progress_margin or 0 for row in progress_rows}

    # Merge all customers
    all_customers = sorted(set(closed_map.keys()) | set(progress_map.keys()))

    combined = []
    for customer in all_customers:
        closed = closed_map.get(customer, 0)
        in_progress = progress_map.get(customer, 0)
        combined.append({
            "customer": customer,
            "closed": closed,
            "in_progress": in_progress,
            "total": closed + in_progress,
        })

    # Sort by total descending
    combined.sort(key=lambda x: x["total"], reverse=True)

    # Top 10 + Others
    data = []
    others_closed = 0
    others_in_progress = 0

    for i, row in enumerate(combined):
        if i < 10:
            data.append({
                "Customer": row["customer"],
                "Closed Margin": row["closed"],
                "In Progress Margin": row["in_progress"],
                "Total Margin": row["total"],
            })
        else:
            others_closed += row["closed"]
            others_in_progress += row["in_progress"]

    if len(combined) > 10:
        data.append({
            "Customer": "Others",
            "Closed Margin": others_closed,
            "In Progress Margin": others_in_progress,
            "Total Margin": others_closed + others_in_progress,
        })

    return data
