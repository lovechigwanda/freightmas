# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "voucher_type",
            "label": _("Voucher Type"),
            "fieldtype": "Data",
            "width": 130
        },
        {
            "fieldname": "voucher_no",
            "label": _("Voucher No"),
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 195,
            "align": "left"
        },
        {
            "fieldname": "debit",
            "label": _("Debit"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "credit",
            "label": _("Credit"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "balance",
            "label": _("Balance"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "remarks",
            "label": _("Remarks"),
            "fieldtype": "Text",
            "width": 340
        }
    ]

def get_data(filters):
    data = []
    
    # Get opening balance
    opening_balance = get_opening_balance(filters)
    balance = opening_balance
    
    # Add opening balance row
    data.append({
        "posting_date": formatdate(filters.get("from_date"), "dd-MMM-yy"),
        "voucher_type": "Opening Balance",
        "voucher_no": "",
        "debit": 0,
        "credit": 0,
        "balance": opening_balance,
        "remarks": "Opening Balance"
    })
    
    conditions = get_conditions(filters)
    
    # Get GL entries for the customer
    gl_entries = frappe.db.sql("""
        SELECT 
            posting_date,
            voucher_type,
            voucher_no,
            account,
            party,
            debit,
            credit,
            remarks
        FROM `tabGL Entry`
        WHERE party_type = 'Customer'
        AND {conditions}
        ORDER BY posting_date, creation
    """.format(conditions=conditions), filters, as_dict=1)

    # Get draft invoices if requested
    if filters.get("include_draft_invoices"):
        draft_invoices = get_draft_invoices(filters)
        
        # Combine and sort by posting date
        all_entries = gl_entries + draft_invoices
        all_entries = sorted(all_entries, key=lambda x: x.posting_date)
    else:
        all_entries = gl_entries

    for entry in all_entries:
        balance += (entry.debit - entry.credit)
        row = {
            "posting_date": formatdate(entry.posting_date, "dd-MMM-yy"),
            "voucher_type": entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "debit": entry.debit,
            "credit": entry.credit,
            "balance": balance,
            "remarks": entry.remarks
        }
        data.append(row)
    
    # Add closing balance row
    data.append({
        "posting_date": formatdate(filters.get("to_date"), "dd-MMM-yy"),
        "voucher_type": "Closing Balance",
        "voucher_no": "",
        "debit": 0,
        "credit": 0,
        "balance": balance,
        "remarks": "Closing Balance"
    })
    
    return data

def get_opening_balance(filters):
    # Get balance before from_date for the specific customer
    balance = frappe.db.sql("""
        SELECT SUM(debit) - SUM(credit) as balance
        FROM `tabGL Entry`
        WHERE party_type = 'Customer'
        AND posting_date < %(from_date)s
        AND company = %(company)s
        {customer_condition}
    """.format(
        customer_condition="AND party = %(customer)s" if filters.get("customer") else ""
    ), filters, as_dict=1)[0].balance
    
    return balance or 0

def get_draft_invoices(filters):
    # Get draft sales invoices for the customer
    draft_invoices = frappe.db.sql("""
        SELECT 
            posting_date,
            'Sales Invoice' as voucher_type,
            name as voucher_no,
            '' as account,
            customer as party,
            grand_total as debit,
            0 as credit,
            CONCAT('Draft Invoice - ', name) as remarks
        FROM `tabSales Invoice`
        WHERE docstatus = 0
        AND customer = %(customer)s
        AND company = %(company)s
        AND posting_date >= %(from_date)s
        AND posting_date <= %(to_date)s
    """, filters, as_dict=1)
    
    return draft_invoices

def get_conditions(filters):
    conditions = []
    
    if filters.get("company"):
        conditions.append("company = %(company)s")
    if filters.get("from_date"):
        conditions.append("posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("posting_date <= %(to_date)s")
    if filters.get("customer"):
        conditions.append("party = %(customer)s")
        
    return " AND ".join(conditions)
