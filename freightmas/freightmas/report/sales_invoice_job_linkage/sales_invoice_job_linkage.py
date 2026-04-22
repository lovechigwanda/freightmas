# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe


# Mapping of job types to their custom fields on Sales Invoice and reference field on the job doctype
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
        {"label": "Invoice Number", "fieldname": "invoice_number", "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
        {"label": "Invoice Date", "fieldname": "invoice_date", "fieldtype": "Date", "width": 110},
        {"label": "Total Amount", "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
        {"label": "Job Type", "fieldname": "job_type", "fieldtype": "Data", "width": 140},
        {"label": "Job Number", "fieldname": "job_number", "fieldtype": "Dynamic Link", "options": "job_type", "width": 160},
        {"label": "Customer Name", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
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
    conditions = ["si.docstatus != 2"]  # Exclude cancelled by default unless filtered
    values = {}

    # At least one job link must exist (flag = 1 OR reference IS NOT NULL for warehouse)
    link_parts = []
    for jt in JOB_TYPES:
        if jt["is_flag"]:
            link_parts.append(f"si.{jt['is_flag']} = 1")
        else:
            link_parts.append(f"si.{jt['ref_field']} IS NOT NULL AND si.{jt['ref_field']} != ''")
    job_link_condition = "(" + " OR ".join(link_parts) + ")"
    conditions.append(job_link_condition)

    if filters.get("from_date"):
        conditions.append("si.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("si.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("customer"):
        conditions.append("si.customer = %(customer)s")
        values["customer"] = filters["customer"]

    if filters.get("company"):
        conditions.append("si.company = %(company)s")
        values["company"] = filters["company"]

    if filters.get("status"):
        status = filters["status"]
        if status == "Draft":
            conditions.append("si.docstatus = 0")
        elif status == "Cancelled":
            # Override the default exclusion of cancelled
            conditions = [c for c in conditions if c != "si.docstatus != 2"]
            conditions.append("si.docstatus = 2")
        elif status == "Return":
            conditions.append("si.is_return = 1")
            conditions.append("si.docstatus = 1")
        elif status == "Paid":
            conditions.append("si.docstatus = 1")
            conditions.append("si.outstanding_amount = 0")
            conditions.append("si.is_return = 0")
        elif status == "Unpaid":
            conditions.append("si.docstatus = 1")
            conditions.append("si.outstanding_amount > 0")
            conditions.append("si.due_date >= CURDATE()")
            conditions.append("si.is_return = 0")
        elif status == "Overdue":
            conditions.append("si.docstatus = 1")
            conditions.append("si.outstanding_amount > 0")
            conditions.append("si.due_date < CURDATE()")
            conditions.append("si.is_return = 0")
        elif status == "Submitted":
            conditions.append("si.docstatus = 1")

    # Filter by job type — narrow to the specific job type's condition
    job_type_filter = filters.get("job_type")
    if job_type_filter:
        for jt in JOB_TYPES:
            if jt["label"] == job_type_filter:
                conditions = [c for c in conditions if c != job_link_condition]
                if jt["is_flag"]:
                    conditions.append(f"si.{jt['is_flag']} = 1")
                else:
                    conditions.append(f"si.{jt['ref_field']} IS NOT NULL AND si.{jt['ref_field']} != ''")
                break

    where_clause = " AND ".join(conditions)

    # Build field list — only include is_flags that exist
    flag_fields = [f"si.{jt['is_flag']}" for jt in JOB_TYPES if jt["is_flag"]]
    ref_fields = [f"si.{jt['ref_field']}" for jt in JOB_TYPES]

    extra_fields = ", ".join(flag_fields + ref_fields)

    query = f"""
        SELECT
            si.name, si.posting_date, si.grand_total, si.customer,
            si.customer_name, si.status, si.docstatus, si.is_return,
            si.outstanding_amount, si.due_date,
            {extra_fields}
        FROM `tabSales Invoice` si
        WHERE {where_clause}
        ORDER BY si.posting_date DESC, si.name DESC
    """

    invoices = frappe.db.sql(query, values, as_dict=True)

    # Build a cache for job references to minimize DB calls
    job_ref_cache = {}

    data = []
    for inv in invoices:
        # Determine linked job(s) — one row per job link
        for jt in JOB_TYPES:
            # Check if this job type is linked
            if jt["is_flag"]:
                if not inv.get(jt["is_flag"]):
                    continue
            else:
                # No flag — check if reference field has a value
                if not inv.get(jt["ref_field"]):
                    continue

            job_name = inv.get(jt["ref_field"])
            if not job_name:
                continue

            # Apply job type filter
            if job_type_filter and jt["label"] != job_type_filter:
                continue

            # Fetch job reference from cache or DB
            cache_key = (jt["doctype"], job_name)
            if cache_key not in job_ref_cache:
                job_ref_cache[cache_key] = frappe.db.get_value(
                    jt["doctype"], job_name, jt["job_ref_field"]
                ) or ""

            # Determine display status
            display_status = get_display_status(inv)

            data.append({
                "invoice_number": inv.name,
                "invoice_date": inv.posting_date,
                "grand_total": inv.grand_total,
                "job_type": jt["label"],
                "job_number": job_name,
                "customer": inv.customer,
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
