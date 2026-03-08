import frappe


def execute():
    """
    The old 'Cash and Bank Balance Report' (detailed transactions) has been
    renamed to 'Cash and Bank Transactions'. A new 'Cash and Bank Balance Report'
    (showing only account balances) now uses that name.

    Delete the old Report doc so bench migrate can recreate both cleanly.
    Also delete the old 'Cash and Bank Transactions' doc if it somehow exists.
    """
    old_reports = [
        "Cash and Bank Balance Report",
        "Cash and Bank Transactions",
    ]
    for report_name in old_reports:
        if frappe.db.exists("Report", report_name):
            frappe.delete_doc("Report", report_name, force=True, ignore_permissions=True)
