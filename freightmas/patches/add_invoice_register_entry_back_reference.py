import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Add the invoice_register_entry back-reference field on Sales Invoice and
    Purchase Invoice so the Invoice Register Entry Document Links (Connections
    tab) can resolve, and backfill it from existing IRE links."""

    create_custom_fields(
        {
            "Sales Invoice": [
                {
                    "fieldname": "invoice_register_entry",
                    "label": "Invoice Register Entry",
                    "fieldtype": "Link",
                    "options": "Invoice Register Entry",
                    "hidden": 1,
                    "read_only": 1,
                    "no_copy": 1,
                    "print_hide": 1,
                    "search_index": 1,
                }
            ],
            "Purchase Invoice": [
                {
                    "fieldname": "invoice_register_entry",
                    "label": "Invoice Register Entry",
                    "fieldtype": "Link",
                    "options": "Invoice Register Entry",
                    "hidden": 1,
                    "read_only": 1,
                    "no_copy": 1,
                    "print_hide": 1,
                    "search_index": 1,
                }
            ],
        },
        update=True,
    )

    for field, doctype in (
        ("linked_sales_invoice", "Sales Invoice"),
        ("linked_purchase_invoice", "Purchase Invoice"),
    ):
        entries = frappe.get_all(
            "Invoice Register Entry",
            filters={field: ["is", "set"]},
            fields=["name", field],
        )
        for entry in entries:
            frappe.db.set_value(
                doctype, entry.get(field), "invoice_register_entry", entry.name, update_modified=False
            )

    frappe.db.commit()
