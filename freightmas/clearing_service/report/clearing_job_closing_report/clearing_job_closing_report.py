# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import formatdate


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Job ID"),
            "fieldname": "job_id",
            "fieldtype": "Link",
            "options": "Clearing Job",
            "width": 150,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180,
        },
        {
            "label": _("Customer Reference"),
            "fieldname": "customer_reference",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Completed On"),
            "fieldname": "completed_on",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Revenue Recognised"),
            "fieldname": "revenue_recognised",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("RR Date"),
            "fieldname": "revenue_recognised_on",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 110,
        },
    ]


def get_data(filters):
    conditions = [
        "cj.status IN ('Completed', 'Closed')",
        "cj.docstatus < 2",
    ]
    params = {}

    if filters.get("status"):
        conditions.append("cj.status = %(status)s")
        params["status"] = filters["status"]

    if filters.get("customer"):
        conditions.append("cj.customer = %(customer)s")
        params["customer"] = filters["customer"]

    where_clause = " AND ".join(conditions)

    jobs = frappe.db.sql(
        """
        SELECT
            cj.name,
            cj.customer,
            cj.customer_reference,
            cj.completed_on,
            cj.revenue_recognised,
            cj.revenue_recognised_on,
            cj.status
        FROM `tabClearing Job` cj
        WHERE {where_clause}
        ORDER BY cj.completed_on DESC
    """.format(
            where_clause=where_clause
        ),
        params,
        as_dict=True,
    )

    data = []
    for job in jobs:
        data.append(
            {
                "job_id": job.name,
                "customer": job.customer or "",
                "customer_reference": job.get("customer_reference") or "",
                "completed_on": format_date(job.get("completed_on")),
                "revenue_recognised": "Yes" if job.get("revenue_recognised") else "No",
                "revenue_recognised_on": format_date(job.get("revenue_recognised_on")),
                "status": job.get("status") or "",
            }
        )

    return data


def format_date(date_value):
    if not date_value:
        return ""
    try:
        return formatdate(date_value, "dd-MMM-yy")
    except Exception:
        return str(date_value)
