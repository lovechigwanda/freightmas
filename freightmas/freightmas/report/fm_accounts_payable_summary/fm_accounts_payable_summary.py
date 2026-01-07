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
            "fieldname": "supplier",
            "label": _("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
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
    supplier = filters.get("supplier")
    supplier_group = filters.get("supplier_group")
    include_drafts = filters.get("include_proforma_invoices")
    report_date = getdate(filters.get("report_date") or frappe.utils.today())
    
    if not company:
        frappe.throw(_("Company filter is required"))
    
    conditions = ["gl.party_type = 'Supplier'", "gl.is_cancelled = 0"]
    pi_conditions = ["pi.docstatus = 0", "pi.is_return = 0"]
    
    if supplier:
        conditions.append("gl.party = %(supplier)s")
        pi_conditions.append("pi.supplier = %(supplier)s")
    
    if supplier_group:
        conditions.append("gl.party IN (SELECT name FROM `tabSupplier` WHERE supplier_group = %(supplier_group)s)")
        pi_conditions.append("pi.supplier IN (SELECT name FROM `tabSupplier` WHERE supplier_group = %(supplier_group)s)")
    
    params = {
        "company": company,
        "supplier": supplier,
        "supplier_group": supplier_group,
        "report_date": report_date,
    }
    
    # Get GL-based outstanding (submitted)
    gl_data = frappe.db.sql(
        f"""
        SELECT
            gl.party AS supplier,
            SUM(gl.credit) - SUM(gl.debit) AS outstanding_submitted
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE
            gl.company = %(company)s
            AND acc.account_type = 'Payable'
            AND gl.posting_date <= %(report_date)s
            AND {" AND ".join(conditions)}
        GROUP BY gl.party
        """,
        params,
        as_dict=True,
    )
    
    gl_map = {row.supplier: flt(row.outstanding_submitted) for row in gl_data}
    
    # Get draft invoices (optional)
    draft_map = {}
    if include_drafts:
        draft_data = frappe.db.sql(
            f"""
            SELECT
                pi.supplier,
                SUM(pi.grand_total) AS outstanding_draft
            FROM `tabPurchase Invoice` pi
            WHERE
                pi.company = %(company)s
                AND pi.posting_date <= %(report_date)s
                AND {" AND ".join(pi_conditions)}
            GROUP BY pi.supplier
            """,
            params,
            as_dict=True,
        )
        draft_map = {row.supplier: flt(row.outstanding_draft) for row in draft_data}
    
    # Merge results
    suppliers = set(gl_map.keys()) | set(draft_map.keys())
    result = []
    
    for supp in suppliers:
        submitted = gl_map.get(supp, 0)
        draft = draft_map.get(supp, 0) if include_drafts else 0
        total = submitted + draft
        
        if total != 0:
            # Get aging analysis
            aging = get_aging_analysis(supp, filters, report_date)
            
            row = {
                "supplier": supp,
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
    result.sort(key=lambda x: (-x["total_outstanding"], x["supplier"]))
    
    return result


def get_aging_analysis(supplier, filters, report_date):
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
        FROM `tabPurchase Invoice`
        WHERE supplier = %(supplier)s
        AND company = %(company)s
        AND docstatus = 1
        AND outstanding_amount > 0
        AND posting_date <= %(report_date)s
        """,
        {"supplier": supplier, "company": company, "report_date": report_date},
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
