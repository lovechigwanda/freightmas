# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


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
    report_date = getdate(filters.get("report_date") or frappe.utils.today())
    
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
    
    # Get supplier outstanding amounts from invoices
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
    
    # Get suppliers from Journal Entries via Payment Ledger Entry
    payable_account = frappe.db.get_value("Company", company, "default_payable_account")
    journal_suppliers = {}
    
    if payable_account:
        je_conditions = f"AND ple.company = '{company}'"
        if supplier:
            je_conditions += f" AND ple.party = '{supplier}'"
        if supplier_group:
            je_conditions += f" AND ple.party IN (SELECT name FROM `tabSupplier` WHERE supplier_group = '{supplier_group}')"
        
        journal_data = frappe.db.sql(f"""
            SELECT 
                ple.party as supplier,
                SUM(ple.amount) as outstanding_amount
            FROM `tabPayment Ledger Entry` ple
            WHERE ple.party_type = 'Supplier'
            AND ple.voucher_type = 'Journal Entry'
            AND ple.account = '{payable_account}'
            AND ple.posting_date <= '{report_date}'
            AND ple.delinked = 0
            {je_conditions}
            GROUP BY ple.party
            HAVING outstanding_amount != 0
        """, as_dict=True)
        
        for row in journal_data:
            journal_suppliers[row.supplier] = flt(row.outstanding_amount)
    
    # Merge invoice and journal entry data
    supplier_map = {}
    for row in data:
        supplier_map[row.supplier] = flt(row.outstanding_amount)
    
    # Add journal entry amounts
    for supplier, je_amount in journal_suppliers.items():
        supplier_map[supplier] = supplier_map.get(supplier, 0) + je_amount
    
    # Rebuild data list
    data = [{"supplier": supp, "outstanding_amount": amt} for supp, amt in supplier_map.items()]
    
    # Get advance amounts for each supplier and subtract from outstanding
    for row in data:
        advance_amount = get_advance_amount(row["supplier"], company)
        row["outstanding_amount"] = flt(row["outstanding_amount"]) - flt(advance_amount)
    
    # Filter out suppliers with zero or negative outstanding after advances
    data = [row for row in data if row["outstanding_amount"] > 0]
    
    # Sort by outstanding amount descending
    data = sorted(data, key=lambda x: (-x["outstanding_amount"], x["supplier"]))
    
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
