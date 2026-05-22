# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, flt


def _fmt_date(d):
    if not d:
        return ""
    try:
        return formatdate(d, "dd-MMM-yy")
    except Exception:
        return str(d)


def execute(filters=None):
    return get_columns(), get_data(filters or {})


def get_columns():
    return [
        {"label": "Job ID",           "fieldname": "job_no",                "fieldtype": "Link",    "options": "Forwarding Job", "width": 140},
        {"label": "Job Date",          "fieldname": "date_created",          "fieldtype": "Data",                                 "width": 100},
        {"label": "Customer",          "fieldname": "customer",              "fieldtype": "Link",    "options": "Customer",       "width": 180},
        {"label": "Ref",               "fieldname": "customer_reference",    "fieldtype": "Data",                                 "width": 130},
        {"label": "Direction",         "fieldname": "direction",             "fieldtype": "Data",                                 "width": 80},
        {"label": "BL No",             "fieldname": "bl_number",             "fieldtype": "Data",                                 "width": 130},
        {"label": "Completed On",      "fieldname": "completed_on",          "fieldtype": "Data",                                 "width": 110},
        {"label": "Rev Recognised",    "fieldname": "revenue_recognised",    "fieldtype": "Data",                                 "width": 110},
        {"label": "Rev Rec Date",      "fieldname": "revenue_recognised_on", "fieldtype": "Data",                                 "width": 110},
        {"label": "Quoted Revenue",    "fieldname": "quoted_revenue",        "fieldtype": "Currency",                             "width": 130},
        {"label": "Quoted Cost",       "fieldname": "quoted_cost",           "fieldtype": "Currency",                             "width": 130},
        {"label": "Quoted Profit",     "fieldname": "quoted_profit",         "fieldtype": "Currency",                             "width": 130},
        {"label": "Quoted Margin %",   "fieldname": "quoted_margin",         "fieldtype": "Percent",                              "width": 100},
        {"label": "Invoiced Revenue",  "fieldname": "invoiced_revenue",      "fieldtype": "Currency",                             "width": 130},
        {"label": "Invoiced Cost",     "fieldname": "invoiced_cost",         "fieldtype": "Currency",                             "width": 130},
        {"label": "Invoiced Profit",   "fieldname": "invoiced_profit",       "fieldtype": "Currency",                             "width": 130},
        {"label": "Invoiced Margin %", "fieldname": "invoiced_margin",       "fieldtype": "Percent",                              "width": 100},
        {"label": "Revenue Variance",  "fieldname": "revenue_variance",      "fieldtype": "Currency",                             "width": 130},
        {"label": "Cost Variance",     "fieldname": "cost_variance",         "fieldtype": "Currency",                             "width": 130},
        {"label": "Profit Variance",   "fieldname": "profit_variance",       "fieldtype": "Currency",                             "width": 130},
    ]


def get_data(filters):
    conditions = ["fj.status IN ('Completed', 'Closed')"]
    values = {}

    if filters.get("from_date"):
        conditions.append("fj.completed_on >= %(from_date)s")
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("fj.completed_on <= %(to_date)s")
        values["to_date"] = filters["to_date"]
    if filters.get("customer"):
        conditions.append("fj.customer = %(customer)s")
        values["customer"] = filters["customer"]
    if filters.get("bl_number"):
        conditions.append("fj.bl_number LIKE %(bl_number)s")
        values["bl_number"] = f"%{filters['bl_number']}%"

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT
            fj.name                              AS job_no,
            fj.date_created,
            fj.customer,
            fj.customer_reference,
            fj.direction,
            fj.bl_number,
            fj.completed_on,
            fj.revenue_recognised,
            fj.revenue_recognised_on,
            fj.total_quoted_revenue_base         AS quoted_revenue,
            fj.total_quoted_cost_base            AS quoted_cost,
            fj.total_quoted_profit_base          AS quoted_profit,
            fj.quoted_margin_percent             AS quoted_margin,
            COALESCE(si.invoiced_revenue, 0)     AS invoiced_revenue,
            COALESCE(pi.invoiced_cost,    0)     AS invoiced_cost
        FROM `tabForwarding Job` fj
        LEFT JOIN (
            SELECT forwarding_job_reference, SUM(grand_total) AS invoiced_revenue
            FROM `tabSales Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference IS NOT NULL
            GROUP BY forwarding_job_reference
        ) si ON si.forwarding_job_reference = fj.name
        LEFT JOIN (
            SELECT forwarding_job_reference, SUM(grand_total) AS invoiced_cost
            FROM `tabPurchase Invoice`
            WHERE docstatus = 1 AND forwarding_job_reference IS NOT NULL
            GROUP BY forwarding_job_reference
        ) pi ON pi.forwarding_job_reference = fj.name
        WHERE {where}
        ORDER BY fj.completed_on DESC
    """, values, as_dict=True)

    data = []
    for row in rows:
        inv_rev  = flt(row.get("invoiced_revenue") or 0)
        inv_cost = flt(row.get("invoiced_cost") or 0)
        inv_prof = inv_rev - inv_cost
        inv_marg = (inv_prof / inv_rev * 100) if inv_rev else 0

        q_rev  = flt(row.get("quoted_revenue") or 0)
        q_cost = flt(row.get("quoted_cost") or 0)
        q_prof = flt(row.get("quoted_profit") or 0)

        data.append({
            "job_no":                row.job_no,
            "date_created":          _fmt_date(row.get("date_created")),
            "customer":              row.get("customer") or "",
            "customer_reference":    row.get("customer_reference") or "",
            "direction":             row.get("direction") or "",
            "bl_number":             row.get("bl_number") or "",
            "completed_on":          _fmt_date(row.get("completed_on")),
            "revenue_recognised":    "Yes" if row.get("revenue_recognised") else "No",
            "revenue_recognised_on": _fmt_date(row.get("revenue_recognised_on")),
            "quoted_revenue":        q_rev,
            "quoted_cost":           q_cost,
            "quoted_profit":         q_prof,
            "quoted_margin":         flt(row.get("quoted_margin") or 0),
            "invoiced_revenue":      inv_rev,
            "invoiced_cost":         inv_cost,
            "invoiced_profit":       inv_prof,
            "invoiced_margin":       inv_marg,
            "revenue_variance":      inv_rev  - q_rev,
            "cost_variance":         inv_cost - q_cost,
            "profit_variance":       inv_prof - q_prof,
        })

    return data
