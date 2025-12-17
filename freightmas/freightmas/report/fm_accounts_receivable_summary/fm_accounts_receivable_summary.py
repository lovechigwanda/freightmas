# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import formatdate, getdate, add_days, flt, cint
from datetime import datetime


def execute(filters=None):
    """Execute the Accounts Receivable Summary report with Proforma option."""
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data


def get_columns(filters):
    """Get column definitions for the AR Summary report."""
    columns = [
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
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
            "fieldname": "credit_note_amount",
            "label": _("Credit Note"),
            "fieldtype": "Currency",
            "width": 120
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
            "label": _("31-60 Days"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "range3",
            "label": _("61-90 Days"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "range4",
            "label": _("91+ Days"),
            "fieldtype": "Currency",
            "width": 100
        }
    ])
    
    return columns


def get_data(filters):
    """Get data for the AR Summary report."""
    report_date = getdate(filters.get("report_date") or frappe.utils.today())
    
    # Get all customers with invoices
    customers = get_customers_with_invoices(filters)
    
    data = []
    for customer in customers:
        row = get_customer_summary(customer, filters, report_date)
        if row:
            data.append(row)
    
    return data


def get_customers_with_invoices(filters):
    """Get list of customers who have sales invoices."""
    conditions = get_conditions(filters)
    
    customers = frappe.db.sql(f"""
        SELECT DISTINCT customer
        FROM `tabSales Invoice`
        WHERE docstatus = 1 {conditions}
        ORDER BY customer
    """, as_dict=True)
    
    return [c.customer for c in customers]


def get_customer_summary(customer, filters, report_date):
    """Get summary data for a single customer."""
    company = filters.get("company")
    
    # Get opening balance (before from_date)
    opening_balance = get_opening_balance(customer, filters)
    
    # Get invoiced amount (submitted invoices in period)
    invoiced_amount = get_invoiced_amount(customer, filters)
    
    # Get proforma amount (draft invoices if checkbox is ticked)
    proforma_amount = 0
    if filters.get("include_proforma_invoices"):
        proforma_amount = get_proforma_amount(customer, filters)
    
    # Get paid amount (payments in period)
    paid_amount = get_paid_amount(customer, filters)
    
    # Get credit note amount
    credit_note_amount = get_credit_note_amount(customer, filters)
    
    # Calculate outstanding amount (include proforma if checkbox is ticked)
    total_invoiced = invoiced_amount
    if filters.get("include_proforma_invoices"):
        total_invoiced += proforma_amount
        
    outstanding_amount = opening_balance + total_invoiced - paid_amount - credit_note_amount
    
    # Get aging analysis (include proforma if checkbox is ticked)
    aging = get_aging_analysis(customer, filters, report_date)
    
    row = {
        "customer": customer,
        "opening_balance": opening_balance,
        "invoiced_amount": invoiced_amount,
        "paid_amount": paid_amount,
        "credit_note_amount": credit_note_amount,
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
    if any([outstanding_amount, invoiced_amount, proforma_amount, paid_amount]):
        return row
    
    return None


def get_opening_balance(customer, filters):
    """Calculate opening balance for customer."""
    # For AR Summary without date ranges, opening balance is 0
    # All invoices are considered in the main calculations
    return 0


def get_invoiced_amount(customer, filters):
    """Get total invoiced amount for customer (submitted invoices only)."""
    conditions = get_conditions(filters)
    
    amount = frappe.db.sql(f"""
        SELECT IFNULL(SUM(grand_total), 0) as amount
        FROM `tabSales Invoice`
        WHERE customer = %s 
        AND docstatus = 1
        {conditions}
    """, customer)[0][0] or 0
    
    return flt(amount)


def get_proforma_amount(customer, filters):
    """Get total proforma (draft) invoice amount for customer."""
    conditions = get_conditions(filters, include_draft=True)
    
    amount = frappe.db.sql(f"""
        SELECT IFNULL(SUM(grand_total), 0) as amount  
        FROM `tabSales Invoice`
        WHERE customer = %s
        AND docstatus = 0
        {conditions}
    """, customer)[0][0] or 0
    
    return flt(amount)


def get_paid_amount(customer, filters):
    """Get total payments received from customer."""
    company = filters.get("company")
    
    amount = frappe.db.sql("""
        SELECT IFNULL(SUM(per.allocated_amount), 0) as amount
        FROM `tabPayment Entry` pe
        JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE pe.party_type = 'Customer'
        AND pe.party = %s
        AND pe.company = %s
        AND pe.docstatus = 1
    """, (customer, company))[0][0] or 0
    
    return flt(amount)


def get_credit_note_amount(customer, filters):
    """Get total credit note amount for customer."""
    conditions = get_conditions(filters)
    
    amount = frappe.db.sql(f"""
        SELECT IFNULL(SUM(grand_total), 0) as amount
        FROM `tabSales Invoice`
        WHERE customer = %s
        AND docstatus = 1
        AND is_return = 1
        {conditions}
    """, customer)[0][0] or 0
    
    return flt(amount)


def get_aging_analysis(customer, filters, report_date):
    """Get aging analysis for customer's outstanding invoices."""
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
        FROM `tabSales Invoice`
        WHERE customer = %s
        AND company = %s
        AND docstatus = 1
        AND outstanding_amount > 0
    """, (customer, company), as_dict=True)
    
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
            FROM `tabSales Invoice`
            WHERE customer = %s
            AND company = %s
            AND docstatus = 0
            AND grand_total > 0
        """, (customer, company), as_dict=True)
        
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
    
    customer = filters.get("customer")
    if customer:
        conditions += f" AND customer = '{customer}'"
    
    customer_group = filters.get("customer_group")
    if customer_group:
        conditions += f" AND customer IN (SELECT name FROM `tabCustomer` WHERE customer_group = '{customer_group}')"
    
    # Include only submitted invoices unless specifically including draft
    if not include_draft:
        conditions += " AND docstatus = 1"
    
    return conditions