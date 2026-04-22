# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_data(filters):
    data = []

    has_clearing_perm = frappe.has_permission("Clearing Job", "read")
    has_forwarding_perm = frappe.has_permission("Forwarding Job", "read")

    if has_clearing_perm:
        data.extend(_get_clearing_rows(filters))

    if has_forwarding_perm:
        data.extend(_get_forwarding_rows(filters))

    data.sort(
        key=lambda row: (
            row.get("job_date") or "",
            row.get("job_id") or "",
        ),
        reverse=True,
    )

    return data


def _get_clearing_rows(filters):
    params = {}
    conditions = ["cpd.parenttype = 'Clearing Job'", "cpd.cargo_type = 'Containerised'"]

    if not cint(filters.get("include_cancelled")):
        conditions.append("cj.docstatus < 2")

    container_value = (filters.get("container_number") or filters.get("container_no") or "").strip()
    if container_value:
        conditions.append("cpd.container_number LIKE %(container_number)s")
        params["container_number"] = f"%{container_value}%"

    if filters.get("bl_number"):
        conditions.append("cj.bl_number LIKE %(bl_number)s")
        params["bl_number"] = f"%{filters.get('bl_number').strip()}%"

    if filters.get("customer"):
        conditions.append("cj.customer = %(customer)s")
        params["customer"] = filters.get("customer")

    if filters.get("from_date"):
        conditions.append("cj.date_created >= %(from_date)s")
        params["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("cj.date_created <= %(to_date)s")
        params["to_date"] = filters.get("to_date")

    where_clause = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            'Clearing' AS service,
            'Clearing Job' AS job_doctype,
            cj.name AS job_id,
            cj.bl_number AS bl_number,
            cpd.container_number AS container_number,
            cpd.container_type AS container_type,
            cj.customer AS customer,
            cj.date_created AS job_date,
            cj.docstatus AS docstatus
        FROM `tabClearing Job` cj
        INNER JOIN `tabCargo Package Details` cpd ON cpd.parent = cj.name
        WHERE {where_clause}
        """,
        params,
        as_dict=True,
    )


def _get_forwarding_rows(filters):
    params = {}
    conditions = ["cpd.parenttype = 'Forwarding Job'", "cpd.cargo_type = 'Containerised'"]

    if not cint(filters.get("include_cancelled")):
        conditions.append("fj.docstatus < 2")

    container_value = (filters.get("container_number") or filters.get("container_no") or "").strip()
    if container_value:
        conditions.append("cpd.container_number LIKE %(container_number)s")
        params["container_number"] = f"%{container_value}%"

    if filters.get("bl_number"):
        conditions.append("fj.bl_number LIKE %(bl_number)s")
        params["bl_number"] = f"%{filters.get('bl_number').strip()}%"

    if filters.get("customer"):
        conditions.append("fj.customer = %(customer)s")
        params["customer"] = filters.get("customer")

    if filters.get("from_date"):
        conditions.append("fj.date_created >= %(from_date)s")
        params["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("fj.date_created <= %(to_date)s")
        params["to_date"] = filters.get("to_date")

    where_clause = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            'Forwarding' AS service,
            'Forwarding Job' AS job_doctype,
            fj.name AS job_id,
            fj.bl_number AS bl_number,
            cpd.container_number AS container_number,
            cpd.container_type AS container_type,
            fj.customer AS customer,
            fj.date_created AS job_date,
            fj.docstatus AS docstatus
        FROM `tabForwarding Job` fj
        INNER JOIN `tabCargo Parcel Details` cpd ON cpd.parent = fj.name
        WHERE {where_clause}
        """,
        params,
        as_dict=True,
    )


def get_columns():
    return [
        {
            "label": "Service",
            "fieldname": "service",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Job Type",
            "fieldname": "job_doctype",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Job ID",
            "fieldname": "job_id",
            "fieldtype": "Dynamic Link",
            "options": "job_doctype",
            "width": 150,
        },
        {
            "label": "BL Number",
            "fieldname": "bl_number",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Container Number",
            "fieldname": "container_number",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Container Type",
            "fieldname": "container_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Customer",
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 170,
        },
        {
            "label": "Job Date",
            "fieldname": "job_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": "Docstatus",
            "fieldname": "docstatus",
            "fieldtype": "Int",
            "width": 90,
        },
    ]
