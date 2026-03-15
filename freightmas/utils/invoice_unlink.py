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


# ========================================================
# BEFORE CANCEL HANDLERS - Allow cancelling invoices
# without forcing cancellation of linked jobs/trips
# ========================================================

def before_sales_invoice_cancel(doc, method=None):
    """Skip linked document checks for job/trip child tables."""
    doc.ignore_linked_doctypes = getattr(doc, "ignore_linked_doctypes", []) + [
        "Forwarding Revenue Charges", "Clearing Revenue Charges", "Trip Revenue Charges",
        "Road Freight Charges", "Forwarding Charges", "Clearing Charges",
        "Trip Bulk Sales Invoice Item",
        "Warehouse Job Storage Charges", "Warehouse Job Rental Charges",
        "Warehouse Job Handling Charges",
        "Border Clearing Revenue Charges"
    ]


def before_purchase_invoice_cancel(doc, method=None):
    """Skip linked document checks for job/trip child tables."""
    doc.ignore_linked_doctypes = getattr(doc, "ignore_linked_doctypes", []) + [
        "Forwarding Cost Charges", "Clearing Cost Charges",
        "Trip Cost Charges", "Trip Other Costs",
        "Road Freight Charges", "Forwarding Charges", "Clearing Charges",
        "Border Clearing Cost Charges"
    ]


def before_journal_entry_cancel(doc, method=None):
    """Skip linked document checks for trip child tables."""
    doc.ignore_linked_doctypes = getattr(doc, "ignore_linked_doctypes", []) + [
        "Trip Other Costs"
    ]


# ========================================================
# ON CANCEL HANDLERS - Unlink references after cancellation
# ========================================================


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

        # Unlink from Road Freight Job charges
        unlink_sales_invoice_from_road_freight_job(doc.name)

        # Unlink from Forwarding Charges (combined revenue/cost child table)
        unlink_sales_invoice_from_forwarding_charges(doc.name)

        # Unlink from Clearing Charges (combined revenue/cost child table)
        unlink_sales_invoice_from_clearing_charges(doc.name)

        # Unlink from Trip Bulk Sales Invoice items
        unlink_sales_invoice_from_trip_bulk_invoice(doc.name)

        # Unlink from Warehouse Job charges
        unlink_sales_invoice_from_warehouse_job(doc.name)

        # Unlink from Border Clearing Job revenue charges
        unlink_sales_invoice_from_border_clearing_job(doc.name)

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

        # Unlink from Road Freight Job charges
        unlink_purchase_invoice_from_road_freight_job(doc.name)

        # Unlink from Forwarding Charges (combined revenue/cost child table)
        unlink_purchase_invoice_from_forwarding_charges(doc.name)

        # Unlink from Clearing Charges (combined revenue/cost child table)
        unlink_purchase_invoice_from_clearing_charges(doc.name)

        # Unlink from Border Clearing Job cost charges
        unlink_purchase_invoice_from_border_clearing_job(doc.name)

    except Exception as e:
        frappe.log_error(
            message=f"Error unlinking cancelled Purchase Invoice {doc.name}: {str(e)}",
            title="Invoice Unlink Error"
        )


def on_journal_entry_cancel(doc, method=None):
    """
    Called when a Journal Entry is cancelled.
    Unlinks the journal entry from any Trip Other Costs rows that reference it.
    """
    try:
        unlink_journal_entry_from_trip(doc.name)
    except Exception as e:
        frappe.log_error(
            message=f"Error unlinking cancelled Journal Entry {doc.name}: {str(e)}",
            title="Journal Entry Unlink Error"
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
    Unlink a Sales Invoice from Clearing Job revenue charges.
    Clears is_invoiced and sales_invoice_reference fields.
    """
    linked_rows = frappe.get_all(
        "Clearing Revenue Charges",
        filters={"sales_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Clearing Revenue Charges",
            row.name,
            {
                "is_invoiced": 0,
                "sales_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Revenue charges in Clearing Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


def unlink_purchase_invoice_from_clearing_job(invoice_name):
    """
    Unlink a Purchase Invoice from Clearing Job cost charges.
    Clears is_purchased and purchase_invoice_reference fields.
    """
    linked_rows = frappe.get_all(
        "Clearing Cost Charges",
        filters={"purchase_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Clearing Cost Charges",
            row.name,
            {
                "is_purchased": 0,
                "purchase_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Purchase Invoice {0} was cancelled. Cost charges in Clearing Job {1} have been unlinked.").format(
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
    Clears is_invoiced and sales_invoice fields.
    """
    # Find all revenue charge rows linked to this invoice
    linked_rows = frappe.get_all(
        "Trip Revenue Charges",
        filters={"sales_invoice": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    # Update each linked row
    for row in linked_rows:
        frappe.db.set_value(
            "Trip Revenue Charges",
            row.name,
            {
                "is_invoiced": 0,
                "sales_invoice": None
            },
            update_modified=False
        )

    # Get unique parent trips and notify
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


# ========================================================
# TRIP JOURNAL ENTRY UNLINKING
# ========================================================

def unlink_journal_entry_from_trip(je_name):
    """
    Unlink a Journal Entry from Trip Other Costs rows.
    Clears is_invoiced and journal_entry fields.
    """
    linked_rows = frappe.get_all(
        "Trip Other Costs",
        filters={"journal_entry": je_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Trip Other Costs",
            row.name,
            {
                "is_invoiced": 0,
                "journal_entry": None
            },
            update_modified=False
        )

    parent_trips = list(set(row.parent for row in linked_rows))
    for trip_name in parent_trips:
        frappe.msgprint(
            _("Journal Entry {0} was cancelled. Other costs in Trip {1} have been unlinked.").format(
                je_name, trip_name
            ),
            alert=True
        )


# ========================================================
# ROAD FREIGHT JOB UNLINKING
# ========================================================

def unlink_sales_invoice_from_road_freight_job(invoice_name):
    """Unlink a Sales Invoice from Road Freight Job charges."""
    linked_rows = frappe.get_all(
        "Road Freight Charges",
        filters={"sales_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Road Freight Charges",
            row.name,
            {
                "is_invoiced": 0,
                "sales_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Revenue charges in Road Freight Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


def unlink_purchase_invoice_from_road_freight_job(invoice_name):
    """Unlink a Purchase Invoice from Road Freight Job charges."""
    linked_rows = frappe.get_all(
        "Road Freight Charges",
        filters={"purchase_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Road Freight Charges",
            row.name,
            {
                "is_purchased": 0,
                "purchase_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Purchase Invoice {0} was cancelled. Cost charges in Road Freight Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


# ========================================================
# FORWARDING CHARGES UNLINKING (combined revenue/cost table)
# ========================================================

def unlink_sales_invoice_from_forwarding_charges(invoice_name):
    """Unlink a Sales Invoice from Forwarding Charges rows."""
    linked_rows = frappe.get_all(
        "Forwarding Charges",
        filters={"sales_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Forwarding Charges",
            row.name,
            {
                "is_invoiced": 0,
                "sales_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Forwarding charges in {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


def unlink_purchase_invoice_from_forwarding_charges(invoice_name):
    """Unlink a Purchase Invoice from Forwarding Charges rows."""
    linked_rows = frappe.get_all(
        "Forwarding Charges",
        filters={"purchase_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Forwarding Charges",
            row.name,
            {
                "is_purchased": 0,
                "purchase_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Purchase Invoice {0} was cancelled. Forwarding charges in {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


# ========================================================
# CLEARING CHARGES UNLINKING (combined revenue/cost table)
# ========================================================

def unlink_sales_invoice_from_clearing_charges(invoice_name):
    """Unlink a Sales Invoice from Clearing Charges rows."""
    linked_rows = frappe.get_all(
        "Clearing Charges",
        filters={"sales_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Clearing Charges",
            row.name,
            {
                "is_invoiced": 0,
                "sales_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Clearing charges in {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


def unlink_purchase_invoice_from_clearing_charges(invoice_name):
    """Unlink a Purchase Invoice from Clearing Charges rows."""
    linked_rows = frappe.get_all(
        "Clearing Charges",
        filters={"purchase_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Clearing Charges",
            row.name,
            {
                "is_purchased": 0,
                "purchase_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Purchase Invoice {0} was cancelled. Clearing charges in {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


# ========================================================
# TRIP BULK SALES INVOICE UNLINKING
# ========================================================

def unlink_sales_invoice_from_trip_bulk_invoice(invoice_name):
    """Unlink a Sales Invoice from Trip Bulk Sales Invoice Item rows."""
    linked_rows = frappe.get_all(
        "Trip Bulk Sales Invoice Item",
        filters={"sales_invoice": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Trip Bulk Sales Invoice Item",
            row.name,
            {"sales_invoice": None},
            update_modified=False
        )

    parent_docs = list(set(row.parent for row in linked_rows))
    for doc_name in parent_docs:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Items in Trip Bulk Sales Invoice {1} have been unlinked.").format(
                invoice_name, doc_name
            ),
            alert=True
        )


# ========================================================
# WAREHOUSE JOB UNLINKING
# ========================================================

def unlink_sales_invoice_from_warehouse_job(invoice_name):
    """Unlink a Sales Invoice from Warehouse Job charge tables."""
    for doctype_name in [
        "Warehouse Job Storage Charges",
        "Warehouse Job Rental Charges",
        "Warehouse Job Handling Charges"
    ]:
        linked_rows = frappe.get_all(
            doctype_name,
            filters={"sales_invoice": invoice_name},
            fields=["name", "parent"]
        )

        if not linked_rows:
            continue

        for row in linked_rows:
            frappe.db.set_value(
                doctype_name,
                row.name,
                {
                    "is_invoiced": 0,
                    "sales_invoice": None
                },
                update_modified=False
            )

        parent_jobs = list(set(row.parent for row in linked_rows))
        for job_name in parent_jobs:
            frappe.msgprint(
                _("Sales Invoice {0} was cancelled. Charges in Warehouse Job {1} have been unlinked.").format(
                    invoice_name, job_name
                ),
                alert=True
            )


# ========================================================
# BORDER CLEARING JOB UNLINKING
# ========================================================

def unlink_sales_invoice_from_border_clearing_job(invoice_name):
    """
    Unlink a Sales Invoice from Border Clearing Job revenue charges.
    Clears is_invoiced and sales_invoice_reference fields.
    """
    linked_rows = frappe.get_all(
        "Border Clearing Revenue Charges",
        filters={"sales_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Border Clearing Revenue Charges",
            row.name,
            {
                "is_invoiced": 0,
                "sales_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Sales Invoice {0} was cancelled. Revenue charges in Border Clearing Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )


def unlink_purchase_invoice_from_border_clearing_job(invoice_name):
    """
    Unlink a Purchase Invoice from Border Clearing Job cost charges.
    Clears is_purchased and purchase_invoice_reference fields.
    """
    linked_rows = frappe.get_all(
        "Border Clearing Cost Charges",
        filters={"purchase_invoice_reference": invoice_name},
        fields=["name", "parent"]
    )

    if not linked_rows:
        return

    for row in linked_rows:
        frappe.db.set_value(
            "Border Clearing Cost Charges",
            row.name,
            {
                "is_purchased": 0,
                "purchase_invoice_reference": None
            },
            update_modified=False
        )

    parent_jobs = list(set(row.parent for row in linked_rows))
    for job_name in parent_jobs:
        frappe.msgprint(
            _("Purchase Invoice {0} was cancelled. Cost charges in Border Clearing Job {1} have been unlinked.").format(
                invoice_name, job_name
            ),
            alert=True
        )
