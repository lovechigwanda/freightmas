# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import json
import base64
from collections import OrderedDict

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
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 220,
        },
        {
            "label": _("Job ID"),
            "fieldname": "job_id",
            "fieldtype": "Link",
            "options": "Forwarding Job",
            "width": 140,
        },
        {
            "label": _("Consignee"),
            "fieldname": "consignee_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Job Reference"),
            "fieldname": "job_reference",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("ETA Date"),
            "fieldname": "eta_date",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Cargo Count"),
            "fieldname": "cargo_count",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Direction"),
            "fieldname": "direction",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Latest Tracking Comment"),
            "fieldname": "current_comment",
            "fieldtype": "Data",
            "width": 280,
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
        "fj.status IN ('Draft', 'In Progress', 'Delivered', 'Completed')",
        "fj.docstatus < 2",
    ]
    params = {}

    if filters.get("customer"):
        conditions.append("fj.customer = %(customer)s")
        params["customer"] = filters["customer"]

    where_clause = " AND ".join(conditions)

    jobs = frappe.db.sql(
        """
        SELECT
            fj.name,
            fj.customer,
            fj.consignee,
            c.customer_name AS consignee_name,
            fj.customer_reference,
            fj.eta,
            fj.cargo_count,
            fj.shipment_mode,
            fj.direction,
            fj.current_comment,
            fj.status
        FROM `tabForwarding Job` fj
        LEFT JOIN `tabCustomer` c ON c.name = fj.consignee
        WHERE {where_clause}
        ORDER BY fj.customer ASC, fj.date_created DESC
    """.format(
            where_clause=where_clause
        ),
        params,
        as_dict=True,
    )

    grouped = OrderedDict()
    for job in jobs:
        cust = job.customer or "Unknown"
        if cust not in grouped:
            grouped[cust] = []
        grouped[cust].append(job)

    data = []
    for customer, customer_jobs in grouped.items():
        # Parent row (customer group header)
        data.append(
            {
                "customer": customer,
                "job_id": "",
                "consignee_name": "",
                "job_reference": "",
                "eta_date": "",
                "cargo_count": "",
                "direction": "",
                "current_comment": "",
                "status": "{} job{}".format(
                    len(customer_jobs), "s" if len(customer_jobs) != 1 else ""
                ),
                "indent": 0,
            }
        )

        # Child rows (individual jobs)
        for job in customer_jobs:
            data.append(
                {
                    "customer": "",
                    "job_id": job.name,
                    "consignee_name": job.get("consignee_name")
                    or job.get("consignee")
                    or "",
                    "job_reference": job.get("customer_reference") or "",
                    "eta_date": format_date(job.get("eta")),
                    "cargo_count": job.get("cargo_count") or "",
                    "direction": build_direction(
                        job.get("shipment_mode"), job.get("direction")
                    ),
                    "current_comment": job.get("current_comment") or "",
                    "status": job.get("status") or "",
                    "indent": 1,
                }
            )

    return data


def build_direction(shipment_mode, direction):
    """Combine shipment_mode and direction into display string like 'Road Import'."""
    parts = []
    if shipment_mode:
        parts.append(shipment_mode)
    if direction:
        parts.append(direction)
    return " ".join(parts)


def format_date(date_value):
    """Format date to dd-MMM-yy format."""
    if not date_value:
        return ""
    try:
        return formatdate(date_value, "dd-MMM-yy")
    except Exception:
        return str(date_value)


@frappe.whitelist()
def generate_management_report_pdf(filters=None):
    """Generate Forwarding Job Tracking Internal PDF grouped by customer."""
    if isinstance(filters, str):
        filters = json.loads(filters)
    if not filters:
        filters = {}

    conditions = [
        "fj.status IN ('Draft', 'In Progress', 'Delivered', 'Completed')",
        "fj.docstatus < 2",
    ]
    params = {}

    if filters.get("customer"):
        conditions.append("fj.customer = %(customer)s")
        params["customer"] = filters["customer"]

    where_clause = " AND ".join(conditions)

    jobs = frappe.db.sql(
        """
        SELECT
            fj.name,
            fj.customer,
            fj.consignee,
            c.customer_name AS consignee_name,
            fj.customer_reference,
            fj.eta,
            fj.cargo_count,
            fj.shipment_mode,
            fj.direction,
            fj.current_comment,
            fj.status
        FROM `tabForwarding Job` fj
        LEFT JOIN `tabCustomer` c ON c.name = fj.consignee
        WHERE {where_clause}
        ORDER BY fj.customer ASC, fj.date_created DESC
    """.format(
            where_clause=where_clause
        ),
        params,
        as_dict=True,
    )

    grouped = OrderedDict()
    for job in jobs:
        cust = job.customer or "Unknown"
        if cust not in grouped:
            grouped[cust] = []
        grouped[cust].append(
            {
                "name": job.name,
                "consignee_name": job.get("consignee_name")
                or job.get("consignee")
                or "",
                "customer_reference": job.get("customer_reference") or "",
                "eta": format_date(job.get("eta")),
                "cargo_count": job.get("cargo_count") or "",
                "direction": build_direction(
                    job.get("shipment_mode"), job.get("direction")
                ),
                "current_comment": job.get("current_comment") or "",
                "status": job.get("status") or "",
            }
        )

    total_jobs = len(jobs)
    total_customers = len(grouped)

    context = {
        "company": frappe.defaults.get_user_default("Company"),
        "customers": grouped,
        "total_jobs": total_jobs,
        "total_customers": total_customers,
        "generated_at": frappe.utils.now_datetime().strftime("%d-%b-%Y %H:%M"),
        "frappe": frappe,
    }

    html = frappe.render_template(
        "freightmas/templates/forwarding_job_tracking_internal.html", context
    )

    pdf = frappe.utils.pdf.get_pdf(
        html,
        options={
            "orientation": "Landscape",
            "page-size": "A4",
            "margin-top": "15mm",
            "margin-right": "15mm",
            "margin-bottom": "15mm",
            "margin-left": "15mm",
            "footer-right": "Page [page] of [topage]",
            "footer-font-size": "8",
        },
    )

    timestamp = frappe.utils.now_datetime().strftime("%Y%m%d_%H%M")
    filename = "Forwarding_Job_Tracking_Internal_{}.pdf".format(timestamp)

    pdf_base64 = base64.b64encode(pdf).decode("utf-8")

    return {"pdf_content": pdf_base64, "filename": filename}
