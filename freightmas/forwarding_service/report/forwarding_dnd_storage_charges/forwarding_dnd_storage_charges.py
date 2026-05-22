# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate, now_datetime, flt


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
        {"label": "Job No",         "fieldname": "job_no",                  "fieldtype": "Link",     "options": "Forwarding Job",  "width": 140},
        {"label": "Customer",       "fieldname": "customer",                "fieldtype": "Link",     "options": "Customer",        "width": 180},
        {"label": "Shp Line",       "fieldname": "shipping_line",           "fieldtype": "Link",     "options": "Shipping Line",   "width": 120},
        {"label": "BL No",          "fieldname": "bl_number",               "fieldtype": "Data",                                   "width": 130},
        {"label": "Direction",      "fieldname": "direction",               "fieldtype": "Data",                                   "width": 80},
        {"label": "Container No",   "fieldname": "container_number",        "fieldtype": "Data",                                   "width": 130},
        {"label": "Type",           "fieldname": "container_type",          "fieldtype": "Link",     "options": "Container Type",  "width": 80},
        {"label": "HZ",             "fieldname": "is_hazardous",            "fieldtype": "Check",                                  "width": 45},
        {"label": "Discharge Date", "fieldname": "discharge_date",          "fieldtype": "Data",                                   "width": 110},
        {"label": "Gate-Out Date",  "fieldname": "gate_out_date",           "fieldtype": "Data",                                   "width": 110},
        {"label": "Empty Return",   "fieldname": "empty_return_date",       "fieldtype": "Data",                                   "width": 110},
        {"label": "At Terminal?",   "fieldname": "still_at_terminal",       "fieldtype": "Data",                                   "width": 85},
        {"label": "DND Free",       "fieldname": "dnd_free_days",           "fieldtype": "Int",                                    "width": 75},
        {"label": "DND Rate/Day",   "fieldname": "dnd_rate_per_day",        "fieldtype": "Currency",                               "width": 105},
        {"label": "Tot DND Days",   "fieldname": "total_dnd_days",          "fieldtype": "Int",                                    "width": 90},
        {"label": "Chgbl DND",      "fieldname": "chargeable_dnd_days",     "fieldtype": "Int",                                    "width": 85},
        {"label": "DND Cost",       "fieldname": "estimated_dnd_cost",      "fieldtype": "Currency",                               "width": 110},
        {"label": "Stor Free",      "fieldname": "storage_free_days",       "fieldtype": "Int",                                    "width": 75},
        {"label": "Stor Rate/Day",  "fieldname": "storage_rate_per_day",    "fieldtype": "Currency",                               "width": 105},
        {"label": "Tot Stor Days",  "fieldname": "total_storage_days",      "fieldtype": "Int",                                    "width": 90},
        {"label": "Chgbl Stor",     "fieldname": "chargeable_storage_days", "fieldtype": "Int",                                    "width": 85},
        {"label": "Storage Cost",   "fieldname": "estimated_storage_cost",  "fieldtype": "Currency",                               "width": 110},
        {"label": "Total Cost",     "fieldname": "total_container_cost",    "fieldtype": "Currency",                               "width": 110},
        {"label": "Ccy",            "fieldname": "rate_card_currency",      "fieldtype": "Data",                                   "width": 55},
    ]


def get_data(filters):
    conditions = [
        "fj.status NOT IN ('Closed', 'Cancelled')",
        "(d.chargeable_dnd_days > 0 OR d.chargeable_storage_days > 0)",
    ]
    values = {}

    if filters.get("from_date"):
        conditions.append("d.discharge_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("d.discharge_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]
    if filters.get("customer"):
        conditions.append("fj.customer = %(customer)s")
        values["customer"] = filters["customer"]
    if filters.get("shipping_line"):
        conditions.append("fj.shipping_line = %(shipping_line)s")
        values["shipping_line"] = filters["shipping_line"]
    if filters.get("direction"):
        conditions.append("fj.direction = %(direction)s")
        values["direction"] = filters["direction"]

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT
            fj.name            AS job_no,
            fj.customer,
            fj.shipping_line,
            fj.bl_number,
            fj.direction,
            fj.port_of_discharge,
            d.container_number,
            d.container_type,
            d.is_hazardous,
            d.discharge_date,
            d.gate_out_date,
            d.empty_return_date,
            d.dnd_free_days,
            d.dnd_rate_per_day,
            d.total_dnd_days,
            d.chargeable_dnd_days,
            d.estimated_dnd_cost,
            d.storage_free_days,
            d.storage_rate_per_day,
            d.total_storage_days,
            d.chargeable_storage_days,
            d.estimated_storage_cost,
            d.total_container_cost,
            d.rate_card_currency
        FROM `tabForwarding Job` fj
        INNER JOIN `tabForwarding DND Storage Detail` d ON d.parent = fj.name
        WHERE {where}
        ORDER BY fj.date_created, fj.name, d.container_number
    """, values, as_dict=True)

    for row in rows:
        row["still_at_terminal"] = "Yes" if not row.get("gate_out_date") else ""
        row["discharge_date"]    = _fmt_date(row.get("discharge_date"))
        row["gate_out_date"]     = _fmt_date(row.get("gate_out_date"))
        row["empty_return_date"] = _fmt_date(row.get("empty_return_date"))

    return rows


# ── Custom PDF export ────────────────────────────────────────────────────────

@frappe.whitelist()
def export_pdf(filters=None):
    import json
    if isinstance(filters, str):
        filters = json.loads(filters)
    filters = filters or {}

    frappe.has_permission("Report", "read", "Forwarding DND Storage Charges", throw=True)

    data = get_data(filters)

    # Group rows by job, accumulating subtotals
    job_order = []
    jobs = {}
    for row in data:
        job_no = row["job_no"]
        if job_no not in jobs:
            job_order.append(job_no)
            jobs[job_no] = {
                "job_no": job_no,
                "customer": row.get("customer", ""),
                "shipping_line": row.get("shipping_line", ""),
                "bl_number": row.get("bl_number", ""),
                "direction": row.get("direction", ""),
                "containers": [],
                "subtotal_dnd": 0.0,
                "subtotal_storage": 0.0,
                "subtotal_total": 0.0,
                "currency": row.get("rate_card_currency", ""),
            }
        entry = jobs[job_no]
        entry["containers"].append(row)
        entry["subtotal_dnd"]     += flt(row.get("estimated_dnd_cost") or 0)
        entry["subtotal_storage"] += flt(row.get("estimated_storage_cost") or 0)
        entry["subtotal_total"]   += flt(row.get("total_container_cost") or 0)

    grand_dnd     = sum(j["subtotal_dnd"]     for j in jobs.values())
    grand_storage = sum(j["subtotal_storage"] for j in jobs.values())
    grand_total   = sum(j["subtotal_total"]   for j in jobs.values())

    def fmt_date(d):
        if not d:
            return ""
        try:
            return formatdate(d, "dd MMM yy")
        except Exception:
            return str(d)

    def fmt_num(n):
        n = flt(n)
        if n == 0:
            return ""
        return "{:,.2f}".format(n)

    # Pre-format dates in container rows for the template
    for job in jobs.values():
        for c in job["containers"]:
            c["discharge_date_fmt"]    = fmt_date(c.get("discharge_date"))
            c["gate_out_date_fmt"]     = fmt_date(c.get("gate_out_date")) or "<em>(open)</em>"
            c["empty_return_date_fmt"] = fmt_date(c.get("empty_return_date"))
            c["estimated_dnd_cost_fmt"]     = fmt_num(c.get("estimated_dnd_cost"))
            c["estimated_storage_cost_fmt"] = fmt_num(c.get("estimated_storage_cost"))
            c["total_container_cost_fmt"]   = fmt_num(c.get("total_container_cost"))
            c["dnd_rate_per_day_fmt"]        = fmt_num(c.get("dnd_rate_per_day"))
            c["storage_rate_per_day_fmt"]    = fmt_num(c.get("storage_rate_per_day"))

    # Format filter summary for display
    filter_parts = []
    if filters.get("from_date"):
        filter_parts.append(f"From: {fmt_date(filters['from_date'])}")
    if filters.get("to_date"):
        filter_parts.append(f"To: {fmt_date(filters['to_date'])}")
    if filters.get("customer"):
        filter_parts.append(f"Customer: {filters['customer']}")
    if filters.get("shipping_line"):
        filter_parts.append(f"Shipping Line: {filters['shipping_line']}")
    if filters.get("direction"):
        filter_parts.append(f"Direction: {filters['direction']}")

    context = {
        "company":        frappe.defaults.get_user_default("Company") or "",
        "filter_summary": "  |  ".join(filter_parts) if filter_parts else "All open jobs",
        "jobs":           [jobs[j] for j in job_order],
        "grand_dnd":      fmt_num(grand_dnd),
        "grand_storage":  fmt_num(grand_storage),
        "grand_total":    fmt_num(grand_total),
        "exported_at":    now_datetime().strftime("%d %b %Y %H:%M"),
    }

    template_path = (
        "freightmas/forwarding_service/report/"
        "forwarding_dnd_storage_charges/forwarding_dnd_storage_charges_pdf.html"
    )
    html = frappe.render_template(template_path, context)

    pdf = frappe.utils.pdf.get_pdf(html, options={
        "orientation": "Landscape",
        "page-size": "A4",
        "margin-top": "12mm",
        "margin-bottom": "18mm",
        "margin-left": "10mm",
        "margin-right": "10mm",
        "encoding": "UTF-8",
        "no-outline": None,
        "footer-right": "Page [page] of [topage]",
        "footer-font-size": "9",
    })

    filename = f"DND_Storage_Charges_{now_datetime().strftime('%Y%m%d_%H%M')}.pdf"
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
    frappe.local.response.content_type = "application/pdf"
