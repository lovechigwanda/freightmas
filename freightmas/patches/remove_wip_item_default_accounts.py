# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
Clear Item Default income/expense accounts that ERPNext's account auto-learning
(set_default_income_account_for_item) captured while invoice items were forced
to the WIP accounts. A WIP account is a holding account, never a valid item
default — leaving it would make the recognition snapshot credit WIP against
itself. The FreightMasSalesInvoice.validate override now prevents new
occurrences; this cleans up rows learned before that guard existed.
"""

import frappe


def execute():
    wip_revenue = frappe.db.get_single_value("FreightMas Settings", "wip_revenue_account")
    wip_cost = frappe.db.get_single_value("FreightMas Settings", "wip_cost_account")

    for fieldname, wip_account in (
        ("income_account", wip_revenue),
        ("expense_account", wip_cost),
    ):
        if not wip_account:
            continue
        frappe.db.sql(
            f"""
            update `tabItem Default`
            set `{fieldname}` = null
            where `{fieldname}` = %s
            """,
            wip_account,
        )

    frappe.clear_cache()
