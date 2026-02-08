# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""
One-time patch to clean up stale references to cancelled documents
in all job charge child tables.

Covers:
- Forwarding Revenue Charges  (sales_invoice_reference → Sales Invoice)
- Forwarding Cost Charges     (purchase_invoice_reference → Purchase Invoice)
- Clearing Revenue Charges    (sales_invoice_reference → Sales Invoice)
- Clearing Cost Charges       (purchase_invoice_reference → Purchase Invoice)
- Trip Revenue Charges        (sales_invoice → Sales Invoice)
- Trip Cost Charges           (purchase_invoice_reference / purchase_invoice → Purchase Invoice)
- Trip Other Costs            (journal_entry → Journal Entry)
- Trip Other Costs            (purchase_invoice_reference / purchase_invoice → Purchase Invoice)
"""

import frappe


def execute():
    """Unlink all cancelled document references from job charge child tables."""

    # Each entry: (child_doctype, link_field, linked_doctype, clear_fields)
    cleanup_map = [
        # Forwarding Job
        (
            "Forwarding Revenue Charges",
            "sales_invoice_reference",
            "Sales Invoice",
            {"sales_invoice_reference": None, "is_invoiced": 0},
        ),
        (
            "Forwarding Cost Charges",
            "purchase_invoice_reference",
            "Purchase Invoice",
            {"purchase_invoice_reference": None, "is_purchased": 0},
        ),
        # Clearing Job
        (
            "Clearing Revenue Charges",
            "sales_invoice_reference",
            "Sales Invoice",
            {"sales_invoice_reference": None, "is_invoiced": 0},
        ),
        (
            "Clearing Cost Charges",
            "purchase_invoice_reference",
            "Purchase Invoice",
            {"purchase_invoice_reference": None, "is_purchased": 0},
        ),
        # Trip
        (
            "Trip Revenue Charges",
            "sales_invoice",
            "Sales Invoice",
            {"sales_invoice": None, "is_invoiced": 0},
        ),
        (
            "Trip Other Costs",
            "journal_entry",
            "Journal Entry",
            {"journal_entry": None, "is_invoiced": 0},
        ),
    ]

    # Trip Cost Charges / Trip Other Costs may have varying field names for purchase invoice
    for doctype_name in ["Trip Cost Charges", "Trip Other Costs"]:
        if not frappe.db.exists("DocType", doctype_name):
            continue

        meta = frappe.get_meta(doctype_name)
        invoice_field = None
        if meta.has_field("purchase_invoice_reference"):
            invoice_field = "purchase_invoice_reference"
        elif meta.has_field("purchase_invoice"):
            invoice_field = "purchase_invoice"

        if invoice_field:
            clear_fields = {invoice_field: None}
            if meta.has_field("is_purchased"):
                clear_fields["is_purchased"] = 0

            cleanup_map.append(
                (doctype_name, invoice_field, "Purchase Invoice", clear_fields)
            )

    total_fixed = 0

    for child_dt, link_field, linked_dt, clear_fields in cleanup_map:
        if not frappe.db.exists("DocType", child_dt):
            continue

        rows = frappe.get_all(
            child_dt,
            filters={link_field: ["is", "set"]},
            fields=["name", "parent", link_field],
        )

        for row in rows:
            linked_name = row.get(link_field)
            if not linked_name:
                continue

            docstatus = frappe.db.get_value(linked_dt, linked_name, "docstatus")

            # docstatus 2 = cancelled, None = deleted/missing
            if docstatus == 2 or docstatus is None:
                frappe.db.set_value(
                    child_dt, row.name, clear_fields, update_modified=False
                )
                total_fixed += 1

    if total_fixed:
        frappe.db.commit()

    print(f"Unlinked {total_fixed} stale cancelled document reference(s).")
