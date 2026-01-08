# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe
from frappe.utils import today, getdate


def expire_quotations():
    """
    Automatically expire quotations that have passed their valid_till date.
    
    Runs daily via scheduler.
    Only affects quotations that are:
    - Submitted (docstatus = 1)
    - In "Approved" or "Sent to Customer" state
    - Past their validity date
    """
    quotations = frappe.get_all(
        "Quotation",
        filters={
            "docstatus": 1,
            "workflow_state": ["in", ["Approved", "Sent to Customer"]],
            "valid_till": ["<", today()]
        },
        pluck="name"
    )

    expired_count = 0
    
    for name in quotations:
        try:
            doc = frappe.get_doc("Quotation", name)
            
            # Double-check state before expiring
            if doc.workflow_state in ["Approved", "Sent to Customer"]:
                doc.workflow_state = "Expired"
                doc.add_comment(
                    "Workflow",
                    f"Automatically expired on {today()} (validity period lapsed)"
                )
                doc.save(ignore_permissions=True)
                frappe.db.commit()
                expired_count += 1
                
        except Exception as e:
            frappe.log_error(
                title=f"Failed to expire quotation {name}",
                message=frappe.get_traceback()
            )
            frappe.db.rollback()
    
    if expired_count > 0:
        frappe.logger().info(f"Expired {expired_count} quotation(s)")
