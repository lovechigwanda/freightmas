# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    return get_columns(), get_data(filters or {})


def get_columns():
    return [
        {"label": "Job ID",                   "fieldname": "name",                 "fieldtype": "Link",     "options": "Forwarding Job", "width": 160},
        {"label": "Customer Name",            "fieldname": "customer",             "fieldtype": "Link",     "options": "Customer",       "width": 180},
        {"label": "Consignee",                "fieldname": "consignee",            "fieldtype": "Link",     "options": "Customer",       "width": 160},
        {"label": "BL Number",                "fieldname": "bl_number",            "fieldtype": "Data",                                  "width": 140},
        {"label": "Cargo Count",              "fieldname": "cargo_count",          "fieldtype": "Int",                                   "width": 90},
        {"label": "Revenue Recognition Date", "fieldname": "revenue_recognised_on","fieldtype": "Date",                                  "width": 140},
        {"label": "Actual Revenue",           "fieldname": "actual_revenue",       "fieldtype": "Currency",                              "width": 140},
        {"label": "Actual Cost",              "fieldname": "actual_cost",          "fieldtype": "Currency",                              "width": 140},
        {"label": "Margin",                   "fieldname": "margin",               "fieldtype": "Currency",                              "width": 130},
        {"label": "Margin %",                 "fieldname": "margin_percent",       "fieldtype": "Percent",                               "width": 100},
    ]


def get_data(filters):
    conditions = ["fj.docstatus = 1", "fj.status != 'Cancelled'"]
    values = {}

    date_field = filters.get("date_field") or "creation"
    date_field_map = {
        "Creation Date": "fj.creation",
        "Revenue Recognition Date": "fj.revenue_recognised_on",
    }
    db_date_field = date_field_map.get(date_field, "fj.creation")

    if filters.get("from_date"):
        conditions.append(f"{db_date_field} >= %(from_date)s")
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append(f"{db_date_field} <= %(to_date)s")
        values["to_date"] = filters["to_date"]
    if filters.get("company"):
        conditions.append("fj.company = %(company)s")
        values["company"] = filters["company"]
    if filters.get("customer"):
        conditions.append("fj.customer = %(customer)s")
        values["customer"] = filters["customer"]
    if filters.get("shipment_mode"):
        conditions.append("fj.shipment_mode = %(shipment_mode)s")
        values["shipment_mode"] = filters["shipment_mode"]
    if filters.get("direction"):
        conditions.append("fj.direction = %(direction)s")
        values["direction"] = filters["direction"]
    if filters.get("status"):
        conditions.append("fj.status = %(status)s")
        values["status"] = filters["status"]

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT
            fj.name,
            fj.customer,
            fj.consignee,
            fj.bl_number,
            fj.cargo_count,
            fj.revenue_recognised_on,
            COALESCE(si.actual_revenue, 0) AS actual_revenue,
            COALESCE(pi.actual_cost,    0) AS actual_cost
        FROM `tabForwarding Job` fj
        LEFT JOIN (
            SELECT forwarding_job_reference, SUM(grand_total) AS actual_revenue
            FROM `tabSales Invoice`
            WHERE docstatus = 1
              AND forwarding_job_reference IS NOT NULL
              AND forwarding_job_reference != ''
            GROUP BY forwarding_job_reference
        ) si ON si.forwarding_job_reference = fj.name
        LEFT JOIN (
            SELECT forwarding_job_reference, SUM(grand_total) AS actual_cost
            FROM `tabPurchase Invoice`
            WHERE docstatus = 1
              AND forwarding_job_reference IS NOT NULL
              AND forwarding_job_reference != ''
            GROUP BY forwarding_job_reference
        ) pi ON pi.forwarding_job_reference = fj.name
        WHERE {where}
        ORDER BY fj.revenue_recognised_on DESC, fj.name DESC
    """, values, as_dict=True)

    data = []
    for row in rows:
        revenue = flt(row.get("actual_revenue") or 0)
        cost    = flt(row.get("actual_cost") or 0)
        margin  = revenue - cost
        margin_pct = (margin / revenue * 100) if revenue else 0

        data.append({
            "name":                 row.name,
            "customer":             row.get("customer") or "",
            "consignee":            row.get("consignee") or "",
            "bl_number":            row.get("bl_number") or "",
            "cargo_count":          row.get("cargo_count") or 0,
            "revenue_recognised_on":row.get("revenue_recognised_on"),
            "actual_revenue":       revenue,
            "actual_cost":          cost,
            "margin":               margin,
            "margin_percent":       flt(margin_pct, 2),
        })

    return data
