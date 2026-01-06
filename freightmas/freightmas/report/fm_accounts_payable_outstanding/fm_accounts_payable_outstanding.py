# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    """Execute the Accounts Payable Outstanding report."""
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data


def get_columns(filters):
    """Get column definitions for the AP Outstanding report."""
    columns = [
        {
            "fieldname": "supplier",
            "label": _("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
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
    """Get data for the AP Outstanding report."""
    company = filters.get("company")
    supplier = filters.get("supplier")
    supplier_group = filters.get("supplier_group")
    include_proforma = filters.get("include_proforma_invoices")
    
    # Build conditions
    conditions = f"AND pi.company = '{company}'"
    
    if supplier:
        conditions += f" AND pi.supplier = '{supplier}'"
    
    if supplier_group:
        conditions += f" AND pi.supplier IN (SELECT name FROM `tabSupplier` WHERE supplier_group = '{supplier_group}')"
    
    # Build docstatus condition
    if include_proforma:
        docstatus_condition = "pi.docstatus IN (0, 1)"
    else:
        docstatus_condition = "pi.docstatus = 1"
    
    # Get supplier outstanding amounts
    data = frappe.db.sql(f"""
        SELECT 
            pi.supplier,
            SUM(CASE 
                WHEN pi.docstatus = 1 THEN pi.outstanding_amount
                ELSE pi.grand_total
            END) as outstanding_amount
        FROM `tabPurchase Invoice` pi
        WHERE {docstatus_condition}
        {conditions}
        GROUP BY pi.supplier
        HAVING outstanding_amount > 0
        ORDER BY outstanding_amount DESC, pi.supplier
    """, as_dict=True)
    
    # Get advance amounts for each supplier
    for row in data:
        advance_amount = get_advance_amount(row.supplier, company)
        row.outstanding_amount = flt(row.outstanding_amount) - flt(advance_amount)
    
    # Filter out suppliers with zero or negative outstanding after advances
    data = [row for row in data if row.outstanding_amount > 0]
    
    return data


def get_advance_amount(supplier, company):
    """Get total unallocated advance payments to supplier."""
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
