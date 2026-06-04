# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
    return get_columns(), get_data(filters or {})


def get_columns():
    return [
        {"label": "Reference",       "fieldname": "reference",      "fieldtype": "Data",    "width": 180},
        {"label": "Type",            "fieldname": "row_type",       "fieldtype": "Data",    "width": 130},
        {"label": "Date",            "fieldname": "date",           "fieldtype": "Date",    "width": 110},
        {"label": "Party",           "fieldname": "party",          "fieldtype": "Data",    "width": 180},
        {"label": "Revenue",         "fieldname": "revenue",        "fieldtype": "Currency","width": 140},
        {"label": "Cost",            "fieldname": "cost",           "fieldtype": "Currency","width": 140},
        {"label": "Margin",          "fieldname": "margin",         "fieldtype": "Currency","width": 130},
        {"label": "Margin %",        "fieldname": "margin_percent", "fieldtype": "Percent", "width": 100},
        {"label": "Outstanding",     "fieldname": "outstanding",    "fieldtype": "Currency","width": 130},
        {"label": "Invoice Status",  "fieldname": "invoice_status", "fieldtype": "Data",    "width": 110},
        {"label": "Journal Entry",   "fieldname": "journal_entry",  "fieldtype": "Link",    "options": "Journal Entry", "width": 170},
    ]


def _invoice_status(row):
    if row.get("is_return"):
        return "Return"
    outstanding = flt(row.get("outstanding_amount") or 0)
    if outstanding == 0:
        return "Paid"
    due_date = row.get("due_date")
    if due_date and getdate(due_date) < getdate(nowdate()):
        return "Overdue"
    return "Unpaid"


def get_data(filters):
    conditions = ["fj.docstatus = 1", "fj.status != 'Cancelled'"]
    values = {}

    date_field_map = {
        "Revenue Recognition Date": "fj.revenue_recognised_on",
    }
    db_date_field = date_field_map.get(filters.get("date_field"), "fj.creation")

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

    jobs = frappe.db.sql(f"""
        SELECT
            fj.name,
            fj.customer,
            fj.consignee,
            fj.bl_number,
            fj.cargo_count,
            fj.status,
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

    if not jobs:
        return []

    job_names = [j.name for j in jobs]

    # Batch-fetch all linked Sales Invoices
    si_list = frappe.db.sql("""
        SELECT name, forwarding_job_reference, posting_date, grand_total,
               outstanding_amount, due_date, is_return, customer,
               recognition_journal_entry
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND forwarding_job_reference IN %(job_names)s
        ORDER BY forwarding_job_reference, posting_date
    """, {"job_names": job_names}, as_dict=True)

    # Batch-fetch all linked Purchase Invoices
    pi_list = frappe.db.sql("""
        SELECT name, forwarding_job_reference, posting_date, grand_total,
               outstanding_amount, due_date, is_return, supplier,
               recognition_journal_entry
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
          AND forwarding_job_reference IN %(job_names)s
        ORDER BY forwarding_job_reference, posting_date
    """, {"job_names": job_names}, as_dict=True)

    # Collect all JE names from invoices for batch fetch
    je_names = list({
        row["recognition_journal_entry"]
        for row in (si_list + pi_list)
        if row.get("recognition_journal_entry")
    })

    # Batch-fetch JE posting dates
    je_dates = {}
    je_amounts = {}
    if je_names:
        for je in frappe.db.sql("""
            SELECT name, posting_date FROM `tabJournal Entry`
            WHERE name IN %(je_names)s
        """, {"je_names": je_names}, as_dict=True):
            je_dates[je.name] = je.posting_date

        for row in frappe.db.sql("""
            SELECT parent,
                   SUM(debit_in_account_currency)  AS total_debit,
                   SUM(credit_in_account_currency) AS total_credit
            FROM `tabJournal Entry Account`
            WHERE parent IN %(je_names)s
            GROUP BY parent
        """, {"je_names": je_names}, as_dict=True):
            je_amounts[row.parent] = {
                "debit": flt(row.total_debit),
                "credit": flt(row.total_credit),
            }

    # Group invoices by job
    si_by_job = {}
    for si in si_list:
        si_by_job.setdefault(si.forwarding_job_reference, []).append(si)

    pi_by_job = {}
    for pi in pi_list:
        pi_by_job.setdefault(pi.forwarding_job_reference, []).append(pi)

    # Build output rows
    data = []
    for job in jobs:
        revenue = flt(job.actual_revenue)
        cost    = flt(job.actual_cost)
        margin  = revenue - cost
        margin_pct = (margin / revenue * 100) if revenue else 0

        # Job header row
        data.append({
            "reference":      job.name,
            "row_type":       "Forwarding Job",
            "date":           job.revenue_recognised_on,
            "party":          f"{job.customer or ''}" + (f" / {job.consignee}" if job.consignee and job.consignee != job.customer else ""),
            "revenue":        revenue,
            "cost":           cost,
            "margin":         margin,
            "margin_percent": flt(margin_pct, 2),
            "outstanding":    None,
            "invoice_status": job.status or "",
            "journal_entry":  None,
            "indent":         0,
            "bold":           1,
        })

        # Revenue invoice child rows
        for si in si_by_job.get(job.name, []):
            si_amount = flt(si.grand_total)
            je_name   = si.get("recognition_journal_entry") or ""
            je_amount = flt(je_amounts.get(je_name, {}).get("credit", 0)) if je_name else None

            data.append({
                "reference":      si.name,
                "row_type":       "Sales Invoice" + (" (Return)" if si.get("is_return") else ""),
                "date":           si.posting_date,
                "party":          si.customer or "",
                "revenue":        si_amount,
                "cost":           None,
                "margin":         None,
                "margin_percent": None,
                "outstanding":    flt(si.outstanding_amount),
                "invoice_status": _invoice_status(si),
                "journal_entry":  je_name or None,
                "indent":         1,
                "bold":           0,
            })

            # Journal Entry row under this SI
            if je_name:
                data.append({
                    "reference":      je_name,
                    "row_type":       "Journal Entry",
                    "date":           je_dates.get(je_name),
                    "party":          "",
                    "revenue":        je_amount,
                    "cost":           None,
                    "margin":         None,
                    "margin_percent": None,
                    "outstanding":    None,
                    "invoice_status": "",
                    "journal_entry":  je_name,
                    "indent":         2,
                    "bold":           0,
                })

        # Cost invoice child rows
        for pi in pi_by_job.get(job.name, []):
            pi_amount = flt(pi.grand_total)
            je_name   = pi.get("recognition_journal_entry") or ""
            je_amount = flt(je_amounts.get(je_name, {}).get("debit", 0)) if je_name else None

            data.append({
                "reference":      pi.name,
                "row_type":       "Purchase Invoice" + (" (Return)" if pi.get("is_return") else ""),
                "date":           pi.posting_date,
                "party":          pi.supplier or "",
                "revenue":        None,
                "cost":           pi_amount,
                "margin":         None,
                "margin_percent": None,
                "outstanding":    flt(pi.outstanding_amount),
                "invoice_status": _invoice_status(pi),
                "journal_entry":  je_name or None,
                "indent":         1,
                "bold":           0,
            })

            # Journal Entry row under this PI
            if je_name:
                data.append({
                    "reference":      je_name,
                    "row_type":       "Journal Entry",
                    "date":           je_dates.get(je_name),
                    "party":          "",
                    "revenue":        None,
                    "cost":           je_amount,
                    "margin":         None,
                    "margin_percent": None,
                    "outstanding":    None,
                    "invoice_status": "",
                    "journal_entry":  je_name,
                    "indent":         2,
                    "bold":           0,
                })

    return data
