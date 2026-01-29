# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""
Invoice Unlink Utilities

This module handles unlinking of cancelled invoices from their source documents
(Forwarding Job, Clearing Job, Trip) to prevent validation errors when editing
the source documents after an invoice has been cancelled.
"""

import frappe
from frappe import _


def on_sales_invoice_cancel(doc, method=None):
    """
    Called when a Sales Invoice is cancelled.
    Unlinks the invoice from any Forwarding Job revenue charges that reference it.
    """
    try:
        # Unlink from Forwarding Job revenue charges
        unlink_sales_invoice_from_forwarding_job(doc.name)
        
        # Unlink from Clearing Job charges
        unlink_sales_invoice_from_clearing_job(doc.name)
        
        # Unlink from Trip revenue charges
        unlink_sales_invoice_from_trip(doc.name)
        
    except Exception as e:
        frappe.log_error(
            message=f"Error unlinking cancelled Sales Invoice {doc.name}: {str(e)}",
            title="Invoice Unlink Error"
        )


def on_purchase_invoice_cancel(doc, method=None):
    """
    Called when a Purchase Invoice is cancelled.
    Unlinks the invoice from any Forwarding Job cost charges that reference it.
    """
    try:
        # Unlink from Forwarding Job cost charges
        unlink_purchase_invoice_from_forwarding_job(doc.name)
        
        # Unlink from Clearing Job charges
        unlink_purchase_invoice_from_clearing_job(doc.name)
        
        # Unlink from Trip cost charges
        unlink_purchase_invoice_from_trip(doc.name)
        
    except Exception as e:
        frappe.log_error(
            message=f"Error unlinking cancelled Purchase Invoice {doc.name}: {str(e)}",
            title="Invoice Unlink Error"
        )


# ========================================================
# FORWARDING JOB UNLINKING
# ========================================================

def unlink_sales_invoice_from_forwarding_job(invoice_name):
    """
    Unlink a Sales Invoice from Forwarding Job revenue charges.
    Clears is_invoiced and sales_invoice_reference fields.
    """
    # Find all revenue charge rows linked to this invoice
    linked_rows = frappe.get_all(
        "Forwarding Revenue Charges",
        filters={"sales_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )
    
    if not linked_rows:
        return
    
    # Update each linked row
    for row in linked_rows:
        frappe.db.set_value(
            "Forwarding Revenue Charges",
            row.name,
            {
                "is_invoiced": 0,
                "sales_invoice_reference": None
            },
            update_modified=False
        )
    
    # Get unique parent jobs and notify
    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Revenue charges in Forwarding Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


def unlink_purchase_invoice_from_forwarding_job(invoice_name):
    """
    Unlink a Purchase Invoice from Forwarding Job cost charges.
    Clears is_purchased and purchase_invoice_reference fields.
    """
    # Find all cost charge rows linked to this invoice
    linked_rows = frappe.get_all(
        "Forwarding Cost Charges",
        filters={"purchase_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )
    
    if not linked_rows:
        return
    
    # Update each linked row
    for row in linked_rows:
        frappe.db.set_value(
            "Forwarding Cost Charges",
            row.name,
            {
                "is_purchased": 0,
                "purchase_invoice_reference": None
            },
            update_modified=False
        )
    
    # Get unique parent jobs and notify
    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Purchase Invoice {0} was cancelled. Cost charges in Forwarding Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


# ========================================================
# CLEARING JOB UNLINKING
# ========================================================

def unlink_sales_invoice_from_clearing_job(invoice_name):
    """
    Unlink a Sales Invoice from Clearing Job charges.
    """
    # Check if Clearing Charges doctype exists and has the required fields
    if not frappe.db.exists("DocType", "Clearing Charges"):
        return
    
    meta = frappe.get_meta("Clearing Charges")
    if not meta.has_field("sales_invoice_reference"):
        return
    
    linked_rows = frappe.get_all(
        "Clearing Charges",
        filters={"sales_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )
    
    if not linked_rows:
        return
    
    update_fields = {"sales_invoice_reference": None}
    if meta.has_field("is_invoiced"):
        update_fields["is_invoiced"] = 0
    
    for row in linked_rows:
        frappe.db.set_value(
            "Clearing Charges",
            row.name,
            update_fields,
            update_modified=False
        )
    
    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Charges in Clearing Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


def unlink_purchase_invoice_from_clearing_job(invoice_name):
    """
    Unlink a Purchase Invoice from Clearing Job charges.
    """
    if not frappe.db.exists("DocType", "Clearing Charges"):
        return
    
    meta = frappe.get_meta("Clearing Charges")
    if not meta.has_field("purchase_invoice_reference"):
        return
    
    linked_rows = frappe.get_all(
        "Clearing Charges",
        filters={"purchase_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )
    
    if not linked_rows:
        return
    
    update_fields = {"purchase_invoice_reference": None}
    if meta.has_field("is_purchased"):
        update_fields["is_purchased"] = 0
    
    for row in linked_rows:
        frappe.db.set_value(
            "Clearing Charges",
            row.name,
            update_fields,
            update_modified=False
        )
    
    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Purchase Invoice {0} was cancelled. Charges in Clearing Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


# ========================================================
# TRIP UNLINKING
# ========================================================

def unlink_sales_invoice_from_trip(invoice_name):
    """
    Unlink a Sales Invoice from Trip revenue charges.
    Note: Trip uses 'sales_invoice' field (not 'sales_invoice_reference')
    """
    if not frappe.db.exists("DocType", "Trip Revenue Charges"):
        return
    
    meta = frappe.get_meta("Trip Revenue Charges")
    
    # Trip Revenue Charges uses 'sales_invoice' field
    invoice_field = None
    if meta.has_field("sales_invoice"):
        invoice_field = "sales_invoice"
    elif meta.has_field("sales_invoice_reference"):
        invoice_field = "sales_invoice_reference"
    else:
        return
    
    linked_rows = frappe.get_all(
        "Trip Revenue Charges",
        filters={invoice_field: invoice_name},
        fields=["name", "parent"]
    )
    
    if not linked_rows:
        return
    
    update_fields = {invoice_field: None}
    if meta.has_field("is_invoiced"):
        update_fields["is_invoiced"] = 0
    
    for row in linked_rows:
        frappe.db.set_value(
            "Trip Revenue Charges",
            row.name,
            update_fields,
            update_modified=False
        )
    
    parent_trips = list(set(row.parent for row in linked_rows))
    for trip_name in parent_trips:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Revenue charges in Trip {1} have been unlinked.").format(
                invoice_name, trip_name
            ),
            alert=True
        )


def unlink_purchase_invoice_from_trip(invoice_name):
    """
    Unlink a Purchase Invoice from Trip cost charges.
    Note: Trip may use different doctype names for cost charges
    """
    # Trip might use Trip Other Costs or Trip Cost Charges
    for doctype_name in ["Trip Cost Charges", "Trip Other Costs"]:
        if not frappe.db.exists("DocType", doctype_name):
            continue
        
        meta = frappe.get_meta(doctype_name)
        
        # Find the purchase invoice reference field
        invoice_field = None
        if meta.has_field("purchase_invoice_reference"):
            invoice_field = "purchase_invoice_reference"
        elif meta.has_field("purchase_invoice"):
            invoice_field = "purchase_invoice"
        else:
            continue
        
        linked_rows = frappe.get_all(
            doctype_name,
            filters={invoice_field: invoice_name},
            fields=["name", "parent"]
        )
        
        if not linked_rows:
            continue
        
        update_fields = {invoice_field: None}
        if meta.has_field("is_purchased"):
            update_fields["is_purchased"] = 0
        
        for row in linked_rows:
            frappe.db.set_value(
                doctype_name,
                row.name,
                update_fields,
                update_modified=False
            )
        
        parent_trips = list(set(row.parent for row in linked_rows))
        for trip_name in parent_trips:
            frappe.msgprint(
                _("Purchase Invoice {0} was cancelled. Cost charges in Trip {1} have been unlinked.").format(
                    invoice_name, trip_name
                ),
                alert=True
            )
