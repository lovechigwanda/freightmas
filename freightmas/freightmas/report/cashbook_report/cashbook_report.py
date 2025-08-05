# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


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
            "fieldname": "voucher_no",
            "label": _("Voucher No"),
            "fieldtype": "Dynamic Link",  # Changed from Link to Dynamic Link
            "options": "voucher_type",    # Will use the voucher_type field to determine document type
            "width": 185,
            "align": "left"
        },
        {
            "fieldname": "remarks",
            "label": _("Remarks"),
            "fieldtype": "Text",
            "width": 500 
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
        "voucher_no": "",  # Empty for opening balance
        "remarks": "Opening Balance",
        "debit": 0,
        "credit": 0,
        "balance": opening_balance
    })
    
    conditions = get_conditions(filters)
    
    gl_entries = frappe.db.sql("""
        SELECT 
            posting_date,
            voucher_type,
            voucher_no,
            account,
            against,
            debit,
            credit,
            remarks
        FROM `tabGL Entry`
        WHERE account in (
            SELECT name 
            FROM tabAccount 
            WHERE account_type in ('Bank', 'Cash')
        )
        AND {conditions}
        ORDER BY posting_date, creation
    """.format(conditions=conditions), filters, as_dict=1)

    for entry in gl_entries:
        balance += (entry.debit - entry.credit)
        row = {
            "posting_date": formatdate(entry.posting_date, "dd-MMM-yy"),
            "voucher_type": entry.voucher_type,  # Added voucher_type
            "voucher_no": entry.voucher_no,
            "remarks": entry.remarks,
            "debit": entry.debit,
            "credit": entry.credit,
            "balance": balance
        }
        data.append(row)
    
    # Add closing balance row
    data.append({
        "posting_date": formatdate(filters.get("to_date"), "dd-MMM-yy"),
        "voucher_no": "",  # Empty for closing balance
        "remarks": "Closing Balance",
        "debit": 0,
        "credit": 0,
        "balance": balance
    })
    
    return data

def get_opening_balance(filters):
    # Get balance before from_date
    balance = frappe.db.sql("""
        SELECT SUM(debit) - SUM(credit) as balance
        FROM `tabGL Entry`
        WHERE account in (
            SELECT name 
            FROM tabAccount 
            WHERE account_type in ('Bank', 'Cash')
        )
        AND posting_date < %(from_date)s
        AND company=%(company)s
        {account_condition}
    """.format(
        account_condition="AND account=%(account)s" if filters.get("account") else ""
    ), filters, as_dict=1)[0].balance
    
    return balance or 0

def get_conditions(filters):
    conditions = []
    
    if filters.get("company"):
        conditions.append("company=%(company)s")
    if filters.get("from_date"):
        conditions.append("posting_date>=%(from_date)s")
    if filters.get("to_date"):
        conditions.append("posting_date<=%(to_date)s")
    if filters.get("account"):
        conditions.append("account=%(account)s")
        
    return " AND ".join(conditions)