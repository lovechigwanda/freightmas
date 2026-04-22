# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe


# Mapping of job types to their custom fields on Purchase Invoice and reference field on the job doctype
JOB_TYPES = [
    {
        "label": "Trip",
        "is_flag": "is_trip_invoice",
        "ref_field": "trip_reference",
        "doctype": "Trip",
        "job_ref_field": "customer_reference",
    },
    {
        "label": "Clearing Job",
        "is_flag": "is_clearing_invoice",
        "ref_field": "clearing_job_reference",
        "doctype": "Clearing Job",
        "job_ref_field": "customer_reference",
    },
    {
        "label": "Forwarding Job",
        "is_flag": "is_forwarding_invoice",
        "ref_field": "forwarding_job_reference",
        "doctype": "Forwarding Job",
        "job_ref_field": "customer_reference",
    },
    {
        "label": "Road Freight Job",
        "is_flag": "is_road_freight_invoice",
        "ref_field": "road_freight_job_reference",
        "doctype": "Road Freight Job",
        "job_ref_field": "customer_reference",
    },
    {
        "label": "Warehouse Job",
        "is_flag": "is_warehouse_invoice",
        "ref_field": "warehouse_job_reference",
        "doctype": "Warehouse Job",
        "job_ref_field": "reference_number",
    },
    {
        "label": "Border Clearing Job",
        "is_flag": "is_border_clearing_invoice",
        "ref_field": "border_clearing_job_reference",
        "doctype": "Border Clearing Job",
        "job_ref_field": "customer_reference",
    },
]


def get_columns():
    return [
        {"label": "Invoice Number", "fieldname": "invoice_number", "fieldtype": "Link", "options": "Purchase Invoice", "width": 160},
        {"label": "Invoice Date", "fieldname": "invoice_date", "fieldtype": "Date", "width": 110},
        {"label": "Total Amount", "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
        {"label": "Job Type", "fieldname": "job_type", "fieldtype": "Data", "width": 140},
        {"label": "Job Number", "fieldname": "job_number", "fieldtype": "Dynamic Link", "options": "job_type", "width": 160},
        {"label": "Supplier Name", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 200},
        {"label": "Job Reference", "fieldname": "job_reference", "fieldtype": "Data", "width": 140},
        {"label": "Invoice Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
    ]


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_data(filters):
    filters = filters or {}

    # Build WHERE conditions
    conditions = ["pi.docstatus != 2"]  # Exclude cancelled by default unless filtered
    values = {}

    # At least one job flag must be set
    job_flag_condition = "(" + " OR ".join(f"pi.{jt['is_flag']} = 1" for jt in JOB_TYPES) + ")"
    conditions.append(job_flag_condition)

    if filters.get("from_date"):
        conditions.append("pi.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("pi.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("supplier"):
        conditions.append("pi.supplier = %(supplier)s")
        values["supplier"] = filters["supplier"]

    if filters.get("company"):
        conditions.append("pi.company = %(company)s")
        values["company"] = filters["company"]

    if filters.get("status"):
        status = filters["status"]
        if status == "Draft":
            conditions.append("pi.docstatus = 0")
        elif status == "Cancelled":
            conditions = [c for c in conditions if c != "pi.docstatus != 2"]
            conditions.append("pi.docstatus = 2")
        elif status == "Return":
            conditions.append("pi.is_return = 1")
            conditions.append("pi.docstatus = 1")
        elif status == "Paid":
            conditions.append("pi.docstatus = 1")
            conditions.append("pi.outstanding_amount = 0")
            conditions.append("pi.is_return = 0")
        elif status == "Unpaid":
            conditions.append("pi.docstatus = 1")
            conditions.append("pi.outstanding_amount > 0")
            conditions.append("pi.due_date >= CURDATE()")
            conditions.append("pi.is_return = 0")
        elif status == "Overdue":
            conditions.append("pi.docstatus = 1")
            conditions.append("pi.outstanding_amount > 0")
            conditions.append("pi.due_date < CURDATE()")
            conditions.append("pi.is_return = 0")
        elif status == "Submitted":
            conditions.append("pi.docstatus = 1")

    # Filter by job type
    job_type_filter = filters.get("job_type")
    if job_type_filter:
        for jt in JOB_TYPES:
            if jt["label"] == job_type_filter:
                conditions = [c for c in conditions if c != job_flag_condition]
                conditions.append(f"pi.{jt['is_flag']} = 1")
                break

    where_clause = " AND ".join(conditions)

    # Build field list
    flag_fields = ", ".join(f"pi.{jt['is_flag']}" for jt in JOB_TYPES)
    ref_fields = ", ".join(f"pi.{jt['ref_field']}" for jt in JOB_TYPES)

    query = f"""
        SELECT
            pi.name, pi.posting_date, pi.grand_total, pi.supplier,
            pi.supplier_name, pi.status, pi.docstatus, pi.is_return,
            pi.outstanding_amount, pi.due_date,
            {flag_fields},
            {ref_fields}
        FROM `tabPurchase Invoice` pi
        WHERE {where_clause}
        ORDER BY pi.posting_date DESC, pi.name DESC
    """

    invoices = frappe.db.sql(query, values, as_dict=True)

    # Build a cache for job references to minimize DB calls
    job_ref_cache = {}

    data = []
    for inv in invoices:
        for jt in JOB_TYPES:
            if not inv.get(jt["is_flag"]):
                continue

            job_name = inv.get(jt["ref_field"])
            if not job_name:
                continue

            if job_type_filter and jt["label"] != job_type_filter:
                continue

            # Fetch job reference from cache or DB
            cache_key = (jt["doctype"], job_name)
            if cache_key not in job_ref_cache:
                job_ref_cache[cache_key] = frappe.db.get_value(
                    jt["doctype"], job_name, jt["job_ref_field"]
                ) or ""

            display_status = get_display_status(inv)

            data.append({
                "invoice_number": inv.name,
                "invoice_date": inv.posting_date,
                "grand_total": inv.grand_total,
                "job_type": jt["label"],
                "job_number": job_name,
                "supplier": inv.supplier,
                "job_reference": job_ref_cache[cache_key],
                "status": display_status,
            })

    return data


def get_display_status(inv):
    """Return a user-friendly status string for the invoice."""
    if inv.docstatus == 0:
        return "Draft"
    if inv.docstatus == 2:
        return "Cancelled"
    if inv.is_return:
        return "Return"
    if inv.outstanding_amount == 0:
        return "Paid"
    if inv.due_date and str(inv.due_date) < frappe.utils.nowdate():
        return "Overdue"
    return "Unpaid"
