# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


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
    
    # Get customer outstanding amounts
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
    
    # Get advance amounts for each customer
    for row in data:
        advance_amount = get_advance_amount(row.customer, company)
        row.outstanding_amount = flt(row.outstanding_amount) - flt(advance_amount)
    
    # Filter out customers with zero or negative outstanding after advances
    data = [row for row in data if row.outstanding_amount > 0]
    
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
