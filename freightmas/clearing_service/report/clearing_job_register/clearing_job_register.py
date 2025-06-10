# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


# Copyright (c) 2025, Your Company

import frappe
from frappe.utils import flt

def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": "Job No.", "fieldname": "name", "fieldtype": "Link", "options": "Clearing Job", "width": 130},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Date", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Customer Ref", "fieldname": "customer_reference", "fieldtype": "Data", "width": 100},
        {"label": "Consignee Ref", "fieldname": "consignee_reference", "fieldtype": "Data", "width": 100},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 80},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 120},
        {"label": "Origin", "fieldname": "origin", "fieldtype": "Data", "width": 120},
        {"label": "Origin Country", "fieldname": "origin_country", "fieldtype": "Data", "width": 100},
        {"label": "Shipping Line", "fieldname": "shipping_line", "fieldtype": "Link", "options": "Shipping Line", "width": 140},
        {"label": "Destination", "fieldname": "destination", "fieldtype": "Data", "width": 120},
        {"label": "Destination Country", "fieldname": "destination_country", "fieldtype": "Data", "width": 100},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Date", "width": 100},
        {"label": "ETD", "fieldname": "etd", "fieldtype": "Date", "width": 100},
        {"label": "Cargo Description", "fieldname": "cargo_description", "fieldtype": "Data", "width": 180},
        {"label": "Hazardous?", "fieldname": "is_hazardous", "fieldtype": "Check", "width": 80},
        {"label": "Cargo Count", "fieldname": "cargo_count", "fieldtype": "Int", "width": 90},
        {"label": "DND Free Days", "fieldname": "dnd_free_days", "fieldtype": "Int", "width": 90},
        {"label": "Port Free Days", "fieldname": "port_free_days", "fieldtype": "Int", "width": 90},
        {"label": "Discharge Date", "fieldname": "discharge_date", "fieldtype": "Date", "width": 100},
        {"label": "Stack Open", "fieldname": "stack_open_date", "fieldtype": "Date", "width": 100},
        {"label": "Stack Close", "fieldname": "stack_close_date", "fieldtype": "Date", "width": 100},
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 80},
        {"label": "Conv. Rate", "fieldname": "conversion_rate", "fieldtype": "Float", "width": 80},
        {"label": "Base Curr.", "fieldname": "base_currency", "fieldtype": "Data", "width": 80},
        {"label": "Est. Revenue (Base)", "fieldname": "total_estimated_revenue_base", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Cost (Base)", "fieldname": "total_estimated_cost_base", "fieldtype": "Currency", "width": 120},
        {"label": "Est. Profit (Base)", "fieldname": "total_estimated_profit_base", "fieldtype": "Currency", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": "Completed On", "fieldname": "completed_on", "fieldtype": "Date", "width": 100},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 100},
        {"label": "Created By", "fieldname": "created_by", "fieldtype": "Data", "width": 110},
    ]

    # Build filters
    conditions = []
    values = {}

    if filters.get("date_from"):
        conditions.append("date_created >= %(date_from)s")
        values["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("date_created <= %(date_to)s")
        values["date_to"] = filters["date_to"]
    if filters.get("direction"):
        conditions.append("direction = %(direction)s")
        values["direction"] = filters["direction"]
    if filters.get("status"):
        conditions.append("status = %(status)s")
        values["status"] = filters["status"]

    where_clause = " where " + " and ".join(conditions) if conditions else ""

    # These are all the base doc fields, not calculated/summaries:
    base_fields = [
        "name", "date_created", "customer", "consignee", "customer_reference", "consignee_reference",
        "direction", "bl_number", "origin", "origin_country", "shipping_line", "destination",
        "destination_country", "eta", "etd", "cargo_description", "is_hazardous",
        "dnd_free_days", "port_free_days", "discharge_date", "stack_open_date", "stack_close_date",
        "currency", "conversion_rate", "base_currency", "status", "completed_on", "company", "created_by"
    ]

    # SQL to get jobs with filters
    jobs = frappe.db.sql(f"""
        SELECT {", ".join(base_fields)}
        FROM `tabClearing Job`
        {where_clause}
        ORDER BY date_created DESC
    """, values, as_dict=1)

    data = []
    for job in jobs:
        cargo_count = job.get("cargo_count", 0)
        total_revenue = total_cost = 0
        charges = frappe.db.get_all("Clearing Charges", filters={"parent": job["name"], "parenttype": "Clearing Job"},
                                   fields=["qty", "sell_rate", "buy_rate"])
        for charge in charges:
            total_revenue += flt(charge.qty) * flt(charge.sell_rate)
            total_cost += flt(charge.qty) * flt(charge.buy_rate)

        conv = flt(job.get("conversion_rate") or 1)
        revenue_base = total_revenue * conv
        cost_base = total_cost * conv
        profit_base = revenue_base - cost_base

        job.update({
            "cargo_count": cargo_count,
            "total_estimated_revenue_base": revenue_base,
            "total_estimated_cost_base": cost_base,
            "total_estimated_profit_base": profit_base,
        })
        data.append(job)

    return columns, data
