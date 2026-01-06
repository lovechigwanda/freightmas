# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    """Execute the Accounts Receivable Outstanding report."""
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data


def get_columns(filters):
    """Get column definitions for the AR Outstanding report."""
    columns = [
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 250
        },
        {
            "fieldname": "outstanding_amount",
            "label": _("Outstanding Amount"),
            "fieldtype": "Currency",
            "width": 180
        }
    ]
    
    return columns


def get_data(filters):
    """Get data for the AR Outstanding report."""
    company = filters.get("company")
    customer = filters.get("customer")
    customer_group = filters.get("customer_group")
    include_proforma = filters.get("include_proforma_invoices")
    report_date = getdate(filters.get("report_date") or frappe.utils.today())
    
    # Build conditions
    conditions = f"AND si.company = '{company}'"
    
    if customer:
        conditions += f" AND si.customer = '{customer}'"
    
    if customer_group:
        conditions += f" AND si.customer IN (SELECT name FROM `tabCustomer` WHERE customer_group = '{customer_group}')"
    
    # Build docstatus condition
    if include_proforma:
        docstatus_condition = "si.docstatus IN (0, 1)"
    else:
        docstatus_condition = "si.docstatus = 1"
    
    # Get customer outstanding amounts from invoices
    data = frappe.db.sql(f"""
        SELECT 
            si.customer,
            SUM(CASE 
                WHEN si.docstatus = 1 THEN si.outstanding_amount
                ELSE si.grand_total
            END) as outstanding_amount
        FROM `tabSales Invoice` si
        WHERE {docstatus_condition}
        {conditions}
        GROUP BY si.customer
        HAVING outstanding_amount > 0
        ORDER BY outstanding_amount DESC, si.customer
    """, as_dict=True)
    
    # Get customers from Journal Entries via Payment Ledger Entry
    receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")
    journal_customers = {}
    
    if receivable_account:
        je_conditions = f"AND ple.company = '{company}'"
        if customer:
            je_conditions += f" AND ple.party = '{customer}'"
        if customer_group:
            je_conditions += f" AND ple.party IN (SELECT name FROM `tabCustomer` WHERE customer_group = '{customer_group}')"
        
        journal_data = frappe.db.sql(f"""
            SELECT 
                ple.party as customer,
                SUM(ple.amount) as outstanding_amount
            FROM `tabPayment Ledger Entry` ple
            WHERE ple.party_type = 'Customer'
            AND ple.voucher_type = 'Journal Entry'
            AND ple.account = '{receivable_account}'
            AND ple.posting_date <= '{report_date}'
            AND ple.delinked = 0
            {je_conditions}
            GROUP BY ple.party
            HAVING outstanding_amount != 0
        """, as_dict=True)
        
        for row in journal_data:
            journal_customers[row.customer] = flt(row.outstanding_amount)
    
    # Merge invoice and journal entry data
    customer_map = {}
    for row in data:
        customer_map[row.customer] = flt(row.outstanding_amount)
    
    # Add journal entry amounts
    for customer, je_amount in journal_customers.items():
        customer_map[customer] = customer_map.get(customer, 0) + je_amount
    
    # Rebuild data list
    data = [{"customer": cust, "outstanding_amount": amt} for cust, amt in customer_map.items()]
    
    # Get advance amounts for each customer and subtract from outstanding
    for row in data:
        advance_amount = get_advance_amount(row["customer"], company)
        row["outstanding_amount"] = flt(row["outstanding_amount"]) - flt(advance_amount)
    
    # Filter out customers with zero or negative outstanding after advances
    data = [row for row in data if row["outstanding_amount"] > 0]
    
    # Sort by outstanding amount descending
    data = sorted(data, key=lambda x: (-x["outstanding_amount"], x["customer"]))
    
    return data


def get_advance_amount(customer, company):
    """Get total unallocated advance payments from customer."""
    # Get total received amount from payment entries
    total_received = frappe.db.sql("""
        SELECT IFNULL(SUM(pe.paid_amount), 0) as amount
        FROM `tabPayment Entry` pe
        WHERE pe.party_type = 'Customer'
        AND pe.party = %s
        AND pe.company = %s
        AND pe.docstatus = 1
        AND pe.payment_type = 'Receive'
    """, (customer, company))[0][0] or 0
    
    # Get total allocated amount
    total_allocated = frappe.db.sql("""
        SELECT IFNULL(SUM(per.allocated_amount), 0) as amount
        FROM `tabPayment Entry` pe
        JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE pe.party_type = 'Customer'
        AND pe.party = %s
        AND pe.company = %s
        AND pe.docstatus = 1
    """, (customer, company))[0][0] or 0
    
    # Unallocated advance = Total received - Total allocated
    advance_amount = flt(total_received) - flt(total_allocated)
    
    return flt(advance_amount) if advance_amount > 0 else 0
