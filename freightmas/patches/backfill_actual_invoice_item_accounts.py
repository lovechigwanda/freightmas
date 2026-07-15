# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
Backfill actual_income_account / actual_expense_account snapshots on invoice
items linked to recognition-wired jobs, so in-flight jobs (invoiced before this
feature) recognize to each charge's own account instead of the flat fallback.
"""

import frappe


SNAPSHOT_FIELDS = {
    "Sales Invoice Item": {
        "fieldname": "actual_income_account",
        "label": "Actual Income Account",
        "insert_after": "income_account",
    },
    "Purchase Invoice Item": {
        "fieldname": "actual_expense_account",
        "label": "Actual Expense Account",
        "insert_after": "expense_account",
    },
}


def ensure_snapshot_fields():
    # Patches run before fixture sync on a fresh migrate, so create the fields
    # here too; create_custom_fields is idempotent and fixture sync will match
    # the same names (dt-fieldname).
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({
        dt: [{
            "fieldname": spec["fieldname"],
            "label": spec["label"],
            "fieldtype": "Link",
            "options": "Account",
            "insert_after": spec["insert_after"],
            "hidden": 1,
            "read_only": 1,
            "print_hide": 1,
            "no_copy": 0,
        }]
        for dt, spec in SNAPSHOT_FIELDS.items()
    }, ignore_validate=True)


def execute():
    ensure_snapshot_fields()

    if not frappe.db.get_single_value("FreightMas Settings", "enable_revenue_recognition"):
        return

    from freightmas.utils.revenue_recognition import (
        RECOGNITION_JOB_TYPES,
        get_recognition_settings,
        resolve_item_default_account,
    )

    settings = get_recognition_settings()
    wip_revenue = settings.get("wip_revenue_account")
    wip_cost = settings.get("wip_cost_account")

    targets = [
        ("Sales Invoice", "Sales Invoice Item", "income_account", "actual_income_account",
         wip_revenue, "revenue_account"),
        ("Purchase Invoice", "Purchase Invoice Item", "expense_account", "actual_expense_account",
         wip_cost, "cost_account"),
    ]

    resolved_cache = {}

    for invoice_doctype, item_doctype, account_field, snapshot_field, wip_account, service_suffix in targets:
        if not wip_account:
            continue

        for link_field, service_type in RECOGNITION_JOB_TYPES.values():
            if not frappe.db.has_column(invoice_doctype, link_field):
                continue

            service_fallback = settings.get(f"{service_type}_{service_suffix}")

            rows = frappe.db.sql(
                f"""
                select child.name, child.item_code, parent.company
                from `tab{item_doctype}` child
                inner join `tab{invoice_doctype}` parent on parent.name = child.parent
                where parent.docstatus < 2
                  and ifnull(parent.`{link_field}`, '') != ''
                  and child.`{account_field}` = %s
                  and ifnull(child.`{snapshot_field}`, '') = ''
                """,
                wip_account,
                as_dict=True,
            )

            for row in rows:
                cache_key = (row.item_code, row.company, account_field, service_type)
                if cache_key not in resolved_cache:
                    resolved_cache[cache_key] = (
                        resolve_item_default_account(row.item_code, row.company, account_field)
                        or service_fallback
                        or frappe.get_cached_value("Company", row.company, f"default_{account_field}")
                    )
                account = resolved_cache[cache_key]
                if account:
                    frappe.db.set_value(
                        item_doctype, row.name, snapshot_field, account,
                        update_modified=False,
                    )
