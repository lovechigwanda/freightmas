# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    filters = filters or {}
    
    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data


def get_columns(filters):
    columns = [
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 200,
        },
        {
            "fieldname": "outstanding_submitted",
            "label": _("Outstanding (Submitted)"),
            "fieldtype": "Currency",
            "width": 160,
        },
    ]
    
    if filters.get("include_proforma_invoices"):
        columns.append({
            "fieldname": "outstanding_draft",
            "label": _("Draft Invoices"),
            "fieldtype": "Currency",
            "width": 140,
        })
    
    columns.extend([
        {
            "fieldname": "total_outstanding",
            "label": _("Total Outstanding"),
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "fieldname": "range1",
            "label": _("0-30 Days"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "range2",
            "label": _("31-60 Days"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "range3",
            "label": _("61-90 Days"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "range4",
            "label": _("91+ Days"),
            "fieldtype": "Currency",
            "width": 100,
        },
    ])
    
    return columns


def get_data(filters):
    company = filters.get("company")
    customer = filters.get("customer")
    customer_group = filters.get("customer_group")
    include_drafts = filters.get("include_proforma_invoices")
    report_date = getdate(filters.get("report_date") or frappe.utils.today())
    
    if not company:
        frappe.throw(_("Company filter is required"))
    
    conditions = ["gl.party_type = 'Customer'", "gl.is_cancelled = 0"]
    si_conditions = ["si.docstatus = 0", "si.is_return = 0"]
    
    if customer:
        conditions.append("gl.party = %(customer)s")
        si_conditions.append("si.customer = %(customer)s")
    
    if customer_group:
        conditions.append("gl.party IN (SELECT name FROM `tabCustomer` WHERE customer_group = %(customer_group)s)")
        si_conditions.append("si.customer IN (SELECT name FROM `tabCustomer` WHERE customer_group = %(customer_group)s)")
    
    params = {
        "company": company,
        "customer": customer,
        "customer_group": customer_group,
        "report_date": report_date,
    }
    
    # Get GL-based outstanding (submitted)
    gl_data = frappe.db.sql(
        f"""
        SELECT
            gl.party AS customer,
            SUM(gl.debit) - SUM(gl.credit) AS outstanding_submitted
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE
            gl.company = %(company)s
            AND acc.account_type = 'Receivable'
            AND gl.posting_date <= %(report_date)s
            AND {" AND ".join(conditions)}
        GROUP BY gl.party
        """,
        params,
        as_dict=True,
    )
    
    gl_map = {row.customer: flt(row.outstanding_submitted) for row in gl_data}
    
    # Get draft invoices (optional)
    draft_map = {}
    if include_drafts:
        draft_data = frappe.db.sql(
            f"""
            SELECT
                si.customer,
                SUM(si.grand_total) AS outstanding_draft
            FROM `tabSales Invoice` si
            WHERE
                si.company = %(company)s
                AND si.posting_date <= %(report_date)s
                AND {" AND ".join(si_conditions)}
            GROUP BY si.customer
            """,
            params,
            as_dict=True,
        )
        draft_map = {row.customer: flt(row.outstanding_draft) for row in draft_data}
    
    # Merge results
    customers = set(gl_map.keys()) | set(draft_map.keys())
    result = []
    
    for cust in customers:
        submitted = gl_map.get(cust, 0)
        draft = draft_map.get(cust, 0) if include_drafts else 0
        total = submitted + draft
        
        if total != 0:
            # Get aging analysis
            aging = get_aging_analysis(cust, filters, report_date)
            
            row = {
                "customer": cust,
                "outstanding_submitted": submitted,
                "total_outstanding": total,
                "range1": aging.get("range1", 0),
                "range2": aging.get("range2", 0),
                "range3": aging.get("range3", 0),
                "range4": aging.get("range4", 0),
            }
            
            if include_drafts:
                row["outstanding_draft"] = draft
            
            result.append(row)
    
    # Sort by total outstanding descending
    result.sort(key=lambda x: (-x["total_outstanding"], x["customer"]))
    
    return result


def get_aging_analysis(customer, filters, report_date):
    """Get aging buckets based on invoices."""
    company = filters.get("company")
    aging_based_on = filters.get("ageing_based_on", "Due Date")
    
    # Parse aging ranges
    aging_range = filters.get("range", "30, 60, 90, 120")
    range_list = [int(x.strip()) for x in aging_range.split(",") if x.strip().isdigit()]
    
    if len(range_list) < 4:
        range_list = [30, 60, 90, 120]
    
    date_field = "due_date" if aging_based_on == "Due Date" else "posting_date"
    
    aging = {"range1": 0, "range2": 0, "range3": 0, "range4": 0}
    
    # Get outstanding invoices
    invoices = frappe.db.sql(
        f"""
        SELECT 
            name,
            {date_field} as ref_date,
            outstanding_amount
        FROM `tabSales Invoice`
        WHERE customer = %(customer)s
        AND company = %(company)s
        AND docstatus = 1
        AND outstanding_amount > 0
        AND posting_date <= %(report_date)s
        """,
        {"customer": customer, "company": company, "report_date": report_date},
        as_dict=True,
    )
    
    for invoice in invoices:
        if not invoice.ref_date:
            continue
        
        days_diff = (report_date - getdate(invoice.ref_date)).days
        amount = flt(invoice.outstanding_amount)
        
        if days_diff <= range_list[0]:
            aging["range1"] += amount
        elif days_diff <= range_list[1]:
            aging["range2"] += amount
        elif days_diff <= range_list[2]:
            aging["range3"] += amount
        else:
            aging["range4"] += amount
    
    return aging
