# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import formatdate, getdate, add_days, flt, cint
from datetime import datetime


def execute(filters=None):
    """Execute the Accounts Payable Summary report with Proforma option."""
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data


def get_columns(filters):
    """Get column definitions for the AP Summary report."""
    columns = [
        {
            "fieldname": "supplier",
            "label": _("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 200
        },
        {
            "fieldname": "opening_balance",
            "label": _("Op Balance"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "invoiced_amount",
            "label": _("Invoiced"),
            "fieldtype": "Currency", 
            "width": 120
        }
    ]
    
    # Add Proforma Amount column if checkbox is ticked
    if filters.get("include_proforma_invoices"):
        columns.append({
            "fieldname": "proforma_amount",
            "label": _("Proforma"),
            "fieldtype": "Currency",
            "width": 120
        })
    
    columns.extend([
        {
            "fieldname": "paid_amount",
            "label": _("Paid"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "advance_amount",
            "label": _("Advance"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "debit_note_amount",
            "label": _("Debit Note"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "outstanding_amount",
            "label": _("Outstanding"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "range1",
            "label": _("0-30 Days"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "range2", 
            "label": _("30-60 Days"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "range3",
            "label": _("60-90 Days"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "range4",
            "label": _("90+ Days"),
            "fieldtype": "Currency",
            "width": 100
        }
    ])
    
    return columns


def get_data(filters):
    """Get data for the AP Summary report."""
    report_date = getdate(filters.get("report_date") or frappe.utils.today())
    
    # Get all suppliers with invoices
    suppliers = get_suppliers_with_invoices(filters)
    
    data = []
    for supplier in suppliers:
        row = get_supplier_summary(supplier, filters, report_date)
        if row:
            data.append(row)
    
    return data


def get_suppliers_with_invoices(filters):
    """Get list of suppliers who have purchase invoices."""
    conditions = get_conditions(filters)
    include_proforma = filters.get("include_proforma_invoices")
    
    # Build the docstatus condition
    if include_proforma:
        # Include both submitted (docstatus=1) and draft (docstatus=0) invoices
        docstatus_condition = "docstatus IN (0, 1)"
    else:
        # Only submitted invoices
        docstatus_condition = "docstatus = 1"
    
    suppliers = frappe.db.sql(f"""
        SELECT DISTINCT supplier
        FROM `tabPurchase Invoice`
        WHERE {docstatus_condition} {conditions}
        ORDER BY supplier
    """, as_dict=True)
    
    return [s.supplier for s in suppliers]


def get_supplier_summary(supplier, filters, report_date):
    """Get summary data for a single supplier."""
    company = filters.get("company")
    
    # Get opening balance
    opening_balance = get_opening_balance(supplier, filters)
    
    # Get invoiced amount (submitted invoices)
    invoiced_amount = get_invoiced_amount(supplier, filters)
    
    # Get proforma amount (draft invoices if checkbox is ticked)
    proforma_amount = 0
    if filters.get("include_proforma_invoices"):
        proforma_amount = get_proforma_amount(supplier, filters)
    
    # Get paid amount (payments)
    paid_amount = get_paid_amount(supplier, filters)
    
    # Get advance amount (unallocated payments)
    advance_amount = get_advance_amount(supplier, filters)
    
    # Get debit note amount
    debit_note_amount = get_debit_note_amount(supplier, filters)
    
    # Calculate outstanding amount
    # When include_proforma_invoices is checked, add proforma_amount to the outstanding balance
    # Advances reduce the outstanding balance
    outstanding_amount = opening_balance + invoiced_amount + proforma_amount - paid_amount - advance_amount - debit_note_amount
    
    # Get aging analysis (include proforma if checkbox is ticked)
    aging = get_aging_analysis(supplier, filters, report_date)
    
    row = {
        "supplier": supplier,
        "opening_balance": opening_balance,
        "invoiced_amount": invoiced_amount,
        "paid_amount": paid_amount,
        "advance_amount": advance_amount,
        "debit_note_amount": debit_note_amount,
        "outstanding_amount": outstanding_amount,
        "range1": aging.get("range1", 0),
        "range2": aging.get("range2", 0), 
        "range3": aging.get("range3", 0),
        "range4": aging.get("range4", 0)
    }
    
    # Add proforma amount if checkbox is ticked
    if filters.get("include_proforma_invoices"):
        row["proforma_amount"] = proforma_amount
    
    # Only return row if there's activity
    if any([outstanding_amount, invoiced_amount, proforma_amount, paid_amount, advance_amount]):
        return row
    
    return None


def get_opening_balance(supplier, filters):
    """Calculate opening balance for supplier."""
    # For AP Summary without date ranges, opening balance is 0
    # All invoices are considered in the main calculations
    return 0


def get_invoiced_amount(supplier, filters):
    """Get total invoiced amount for supplier (submitted invoices only)."""
    conditions = get_conditions(filters)
    
    amount = frappe.db.sql(f"""
        SELECT IFNULL(SUM(grand_total), 0) as amount
        FROM `tabPurchase Invoice`
        WHERE supplier = %s 
        AND docstatus = 1
        {conditions}
    """, supplier)[0][0] or 0
    
    return flt(amount)


def get_proforma_amount(supplier, filters):
    """Get total proforma (draft) invoice amount for supplier."""
    conditions = get_conditions(filters, include_draft=True)
    
    amount = frappe.db.sql(f"""
        SELECT IFNULL(SUM(grand_total), 0) as amount  
        FROM `tabPurchase Invoice`
        WHERE supplier = %s
        AND docstatus = 0
        {conditions}
    """, supplier)[0][0] or 0
    
    return flt(amount)


def get_paid_amount(supplier, filters):
    """Get total payments made to supplier."""
    company = filters.get("company")
    
    amount = frappe.db.sql("""
        SELECT IFNULL(SUM(per.allocated_amount), 0) as amount
        FROM `tabPayment Entry` pe
        JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE pe.party_type = 'Supplier'
        AND pe.party = %s
        AND pe.company = %s
        AND pe.docstatus = 1
    """, (supplier, company))[0][0] or 0
    
    return flt(amount)


def get_advance_amount(supplier, filters):
    """Get total unallocated advance payments to supplier."""
    company = filters.get("company")
    
    # Get total paid amount to supplier from payment entries
    total_paid = frappe.db.sql("""
        SELECT IFNULL(SUM(pe.paid_amount), 0) as amount
        FROM `tabPayment Entry` pe
        WHERE pe.party_type = 'Supplier'
        AND pe.party = %s
        AND pe.company = %s
        AND pe.docstatus = 1
        AND pe.payment_type = 'Pay'
    """, (supplier, company))[0][0] or 0
    
    # Get total allocated amount
    total_allocated = frappe.db.sql("""
        SELECT IFNULL(SUM(per.allocated_amount), 0) as amount
        FROM `tabPayment Entry` pe
        JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE pe.party_type = 'Supplier'
        AND pe.party = %s
        AND pe.company = %s
        AND pe.docstatus = 1
    """, (supplier, company))[0][0] or 0
    
    # Unallocated advance = Total paid - Total allocated
    advance_amount = flt(total_paid) - flt(total_allocated)
    
    return flt(advance_amount) if advance_amount > 0 else 0


def get_debit_note_amount(supplier, filters):
    """Get total debit note amount for supplier."""
    conditions = get_conditions(filters)
    
    amount = frappe.db.sql(f"""
        SELECT IFNULL(SUM(grand_total), 0) as amount
        FROM `tabPurchase Invoice`
        WHERE supplier = %s
        AND docstatus = 1
        AND is_return = 1
        {conditions}
    """, supplier)[0][0] or 0
    
    return flt(amount)


def get_aging_analysis(supplier, filters, report_date):
    """Get aging analysis for supplier's outstanding invoices."""
    company = filters.get("company")
    aging_based_on = filters.get("ageing_based_on", "Due Date")
    include_proforma = filters.get("include_proforma_invoices")
    
    # Parse aging ranges
    aging_range = filters.get("range", "30, 60, 90, 120")
    range_list = [int(x.strip()) for x in aging_range.split(",")]
    
    if len(range_list) < 4:
        range_list = [30, 60, 90, 120]  # Default ranges
    
    # Get outstanding invoices
    date_field = "due_date" if aging_based_on == "Due Date" else "posting_date"
    
    aging = {"range1": 0, "range2": 0, "range3": 0, "range4": 0}
    
    # Get submitted invoices with outstanding amounts
    submitted_invoices = frappe.db.sql(f"""
        SELECT name, {date_field} as ref_date, outstanding_amount as amount
        FROM `tabPurchase Invoice`
        WHERE supplier = %s
        AND company = %s
        AND docstatus = 1
        AND outstanding_amount > 0
    """, (supplier, company), as_dict=True)
    
    # Process submitted invoices
    for invoice in submitted_invoices:
        if not invoice.ref_date:
            continue
            
        days_diff = (report_date - getdate(invoice.ref_date)).days
        amount = flt(invoice.amount)
        
        if days_diff <= range_list[0]:
            aging["range1"] += amount
        elif days_diff <= range_list[1]:
            aging["range2"] += amount
        elif days_diff <= range_list[2]:
            aging["range3"] += amount
        else:
            aging["range4"] += amount
    
    # If including proforma invoices, add draft invoices to aging
    if include_proforma:
        draft_invoices = frappe.db.sql(f"""
            SELECT name, {date_field} as ref_date, grand_total as amount
            FROM `tabPurchase Invoice`
            WHERE supplier = %s
            AND company = %s
            AND docstatus = 0
            AND grand_total > 0
        """, (supplier, company), as_dict=True)
        
        # Process draft invoices
        for invoice in draft_invoices:
            if not invoice.ref_date:
                continue
                
            days_diff = (report_date - getdate(invoice.ref_date)).days
            amount = flt(invoice.amount)
            
            if days_diff <= range_list[0]:
                aging["range1"] += amount
            elif days_diff <= range_list[1]:
                aging["range2"] += amount
            elif days_diff <= range_list[2]:
                aging["range3"] += amount
            else:
                aging["range4"] += amount
    
    return aging


def get_conditions(filters, include_draft=False):
    """Build SQL conditions based on filters."""
    conditions = ""
    
    company = filters.get("company")
    if company:
        conditions += f" AND company = '{company}'"
    
    supplier = filters.get("supplier")
    if supplier:
        conditions += f" AND supplier = '{supplier}'"
    
    supplier_group = filters.get("supplier_group")
    if supplier_group:
        conditions += f" AND supplier IN (SELECT name FROM `tabSupplier` WHERE supplier_group = '{supplier_group}')"
    
    # Include only submitted invoices unless specifically including draft
    if not include_draft:
        conditions += " AND docstatus = 1"
    
    return conditions
