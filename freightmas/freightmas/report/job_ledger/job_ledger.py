# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Job Ledger — every GL posting belonging to a job in one view.

Collects the GL entries of all vouchers tied to a job: its Sales/Purchase
Invoices, the revenue/cost recognition Journal Entries, late-invoice
recognition JEs, and reversal JEs (found via the job name stamped in JE line
remarks). Detail mode shows one row per GL line (per charge); consolidated
mode shows one row per voucher and account with a job-level remark.

Modes:
- Single job: pick a Job — its full ledger is shown; From/To Date (optional)
  limit the GL posting dates.
- Period: leave Job empty — From/To Date select the jobs (by Date Created or
  Revenue Recognised On), and each selected job's FULL ledger is shown with
  a Job column and per-job subtotals, so per-job totals always balance.
"""

import frappe
from frappe import _
from frappe.utils import flt

DATE_BASIS_FIELDS = {
    "Date Created": "date_created",
    "Revenue Recognised On": "revenue_recognised_on",
}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("job_type"):
        return get_columns(filters), []

    if filters.get("job"):
        jobs = [filters.job]
    else:
        if not (filters.get("from_date") and filters.get("to_date")):
            frappe.throw(_("Select a Job, or set From Date and To Date to list all jobs in the period"))
        jobs = get_jobs_in_period(filters)
        if not jobs:
            return get_columns(filters), []

    voucher_job_map = get_job_vouchers(filters, jobs)
    if not voucher_job_map:
        return get_columns(filters), []

    data = get_gl_entries(filters, voucher_job_map)
    if filters.get("consolidated"):
        data = consolidate(filters, data, jobs)

    if not filters.get("job"):
        data = add_job_subtotals(data)
    add_total_row(data)
    return get_columns(filters), data


def get_columns(filters):
    columns = []
    if not filters.get("job"):
        columns.append({
            "label": _("Job"), "fieldname": "job", "fieldtype": "Link",
            "options": filters.get("job_type"), "width": 150,
        })
    columns += [
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 120},
        {"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link",
         "options": "voucher_type", "width": 180},
        {"label": _("Account"), "fieldname": "account", "fieldtype": "Link",
         "options": "Account", "width": 220},
        {"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency",
         "options": "currency", "width": 120},
        {"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency",
         "options": "currency", "width": 120},
        {"label": _("Against Account"), "fieldname": "against", "fieldtype": "Data", "width": 150},
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 400},
    ]
    return columns


def get_jobs_in_period(filters):
    """Jobs of the selected type whose basis date falls in the period."""
    date_field = DATE_BASIS_FIELDS.get(filters.get("date_basis")) or "date_created"
    return frappe.get_all(
        filters.job_type,
        filters={
            "company": filters.company,
            date_field: ("between", [filters.from_date, filters.to_date]),
        },
        pluck="name",
    )


def get_job_vouchers(filters, jobs):
    """Map every (voucher_type, voucher_no) belonging to the jobs to its job."""
    from freightmas.utils.revenue_recognition import JOB_LINK_FIELD_MAP

    job_type = filters.job_type
    link_field = JOB_LINK_FIELD_MAP.get(job_type)
    if not link_field:
        frappe.throw(_("Unsupported job type: {0}").format(job_type))

    docstatus = [1, 2] if filters.get("show_cancelled") else [1]
    voucher_job_map = {}
    je_job_map = {}

    for invoice_doctype in ("Sales Invoice", "Purchase Invoice"):
        if not frappe.db.has_column(invoice_doctype, link_field):
            continue
        invoices = frappe.get_all(
            invoice_doctype,
            filters={link_field: ("in", jobs), "docstatus": ("in", docstatus)},
            fields=["name", f"`{link_field}` as job", "recognition_journal_entry"],
        )
        for inv in invoices:
            voucher_job_map[(invoice_doctype, inv.name)] = inv.job
            if inv.recognition_journal_entry:
                je_job_map[inv.recognition_journal_entry] = inv.job

    # Main recognition JEs stored on the jobs
    for row in frappe.get_all(
        job_type,
        filters={"name": ("in", jobs)},
        fields=["name", "revenue_recognition_journal_entry", "cost_recognition_journal_entry"],
    ):
        for je in (row.revenue_recognition_journal_entry, row.cost_recognition_journal_entry):
            if je:
                je_job_map[je] = row.name

    # Recognition and reversal JEs carry the job name in their line remarks.
    # One scan for all jobs, attributed back in Python.
    like_conditions = " or ".join(f"user_remark like %(job_{i})s" for i in range(len(jobs)))
    values = {f"job_{i}": f"%{job}%" for i, job in enumerate(jobs)}
    values["docstatus"] = docstatus
    remark_rows = frappe.db.sql(
        f"""
        select distinct parent, user_remark
        from `tabJournal Entry Account`
        where docstatus in %(docstatus)s and ({like_conditions})
        """,
        values,
        as_dict=True,
    )
    for row in remark_rows:
        for job in jobs:
            if job in (row.user_remark or ""):
                je_job_map.setdefault(row.parent, job)
                break

    for je, job in je_job_map.items():
        voucher_job_map[("Journal Entry", je)] = job

    return voucher_job_map


def get_gl_entries(filters, voucher_job_map):
    currency = frappe.get_cached_value("Company", filters.company, "default_currency")
    vouchers = list(voucher_job_map)

    conditions = ["gle.company = %(company)s"]
    if not filters.get("show_cancelled"):
        conditions.append("gle.is_cancelled = 0")
    if filters.get("job"):
        # Single-job mode: dates limit the postings shown.
        # Period mode: dates select the jobs; the full ledger is shown.
        if filters.get("from_date"):
            conditions.append("gle.posting_date >= %(from_date)s")
        if filters.get("to_date"):
            conditions.append("gle.posting_date <= %(to_date)s")

    voucher_condition = " or ".join(
        f"(gle.voucher_type = %(vt_{i})s and gle.voucher_no = %(vn_{i})s)"
        for i in range(len(vouchers))
    )
    conditions.append(f"({voucher_condition})")

    values = {"company": filters.company,
              "from_date": filters.get("from_date"), "to_date": filters.get("to_date")}
    for i, (vt, vn) in enumerate(vouchers):
        values[f"vt_{i}"] = vt
        values[f"vn_{i}"] = vn

    rows = frappe.db.sql(
        f"""
        select gle.posting_date, gle.voucher_type, gle.voucher_no, gle.account,
               gle.debit, gle.credit, gle.against, gle.remarks
        from `tabGL Entry` gle
        where {" and ".join(conditions)}
        order by gle.posting_date, gle.voucher_type, gle.voucher_no, gle.creation
        """,
        values,
        as_dict=True,
    )

    for row in rows:
        row.currency = currency
        row.job = voucher_job_map.get((row.voucher_type, row.voucher_no))
    rows.sort(key=lambda r: (r.job or "", str(r.posting_date), r.voucher_type, r.voucher_no))
    return rows


def consolidate(filters, rows, jobs):
    """One row per (job, voucher, account) with a job-level remark."""
    refs = {
        row.name: row.customer_reference
        for row in frappe.get_all(
            filters.job_type,
            filters={"name": ("in", jobs)},
            fields=["name", "customer_reference"],
        )
    }

    grouped = {}
    for row in rows:
        key = (row.job, row.voucher_type, row.voucher_no, row.account)
        if key not in grouped:
            row = frappe._dict(row)
            row.remarks = f"{row.job}, Ref: {refs.get(row.job) or 'N/A'}"
            grouped[key] = row
        else:
            grouped[key].debit = flt(grouped[key].debit) + flt(row.debit)
            grouped[key].credit = flt(grouped[key].credit) + flt(row.credit)
    return list(grouped.values())


def add_job_subtotals(rows):
    """Insert a subtotal row after each job's block (rows are sorted by job)."""
    out = []
    current_job = None
    job_debit = job_credit = 0
    currency = rows[0].get("currency") if rows else None

    def subtotal(job, debit, credit):
        label = _("Total — {0}").format(job)
        return frappe._dict({
            "account": label,
            "debit": debit, "credit": credit,
            "currency": currency, "bold": 1,
            # markers used by the shared Excel/PDF export builders
            "is_group_total": 1, "account_name": label,
        })

    for row in rows:
        if current_job is not None and row.job != current_job:
            out.append(subtotal(current_job, job_debit, job_credit))
            job_debit = job_credit = 0
        current_job = row.job
        job_debit += flt(row.debit)
        job_credit += flt(row.credit)
        out.append(row)

    if current_job is not None:
        out.append(subtotal(current_job, job_debit, job_credit))
    return out


def add_total_row(data):
    if not data:
        return
    entry_rows = [r for r in data if r.get("voucher_no")]
    currency = data[0].get("currency")
    data.append(frappe._dict({
        "account": _("Total"),
        "debit": sum(flt(r.debit) for r in entry_rows),
        "credit": sum(flt(r.credit) for r in entry_rows),
        "currency": currency,
        "bold": 1,
        # markers used by the shared Excel/PDF export builders
        "is_group_total": 1, "account_name": _("Grand Total"),
    }))


# ----------------------------------------
# Excel & PDF Export
# ----------------------------------------

# Columns the export builders should exclude (keep account — this is a ledger)
EXPORT_DROP = ["voucher_type", "party", "party_type"]


def get_export_payload(filters):
    """
    Run the report and shape it for the shared export builders: text columns
    first, Debit/Credit last (total rows merge their label across the leading
    text columns, so currency columns must sit at the end).
    """
    import json
    if isinstance(filters, str):
        filters = json.loads(filters)
    filters = frappe._dict(filters)

    columns, data = execute(filters)

    order = ["job", "posting_date", "voucher_type", "voucher_no",
             "account", "against", "remarks", "debit", "credit"]
    columns = sorted(
        [c for c in columns if c["fieldname"] in order],
        key=lambda c: order.index(c["fieldname"]),
    )
    return filters, columns, data


@frappe.whitelist()
def export_excel(filters):
    """Generate and download a formatted Excel report."""
    filters, columns, data = get_export_payload(filters)

    from freightmas.freightmas.report.report_export_utils import build_excel_file, send_excel_response

    file_bytes = build_excel_file(
        filters=filters,
        data=data,
        columns=columns,
        report_title="Job Ledger",
        drop_fieldnames=EXPORT_DROP,
    )
    send_excel_response(file_bytes, "Job_Ledger.xlsx")


@frappe.whitelist()
def export_pdf(filters):
    """Generate and download a formatted PDF report."""
    filters, columns, data = get_export_payload(filters)

    from freightmas.freightmas.report.report_export_utils import build_pdf_file, send_pdf_response

    file_bytes = build_pdf_file(
        filters=filters,
        data=data,
        columns=columns,
        report_title="Job Ledger",
        drop_fieldnames=EXPORT_DROP,
    )
    send_pdf_response(file_bytes, "Job_Ledger.pdf")
