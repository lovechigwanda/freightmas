# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe

def execute():
    """
    Delete old report records that were renamed:
    - 'Cost of Sales Detail Report' -> 'Direct Expenses Detail Report'
    - 'Expenses Detail Report' -> 'Indirect Expenses Detail Report'

    The report folders were renamed but the old Report docs remain in the
    database, causing bench migrate to fail because the corresponding
    Python files no longer exist on disk.
    """
    old_reports = [
        "Cost of Sales Detail Report",
        "Expenses Detail Report",
    ]

    for report_name in old_reports:
        if frappe.db.exists("Report", report_name):
            frappe.delete_doc("Report", report_name, force=True, ignore_permissions=True)
            print(f"Deleted old report: {report_name}")
