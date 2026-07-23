# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Data migration (2026-07-23): replace the entire Port Clearance Milestone
Definition set with a new fixed 15-step checklist, and rebuild the
port_clearance_milestones checklist (unchecked) on every Forwarding Job that
currently has Port Clearance enabled.

This intentionally bypasses Forwarding Job's normal milestone guards
(prevent_milestone_row_deletion / prevent_manual_milestone_rows) by editing
Job Milestone Progress rows directly at the DB layer instead of going
through ForwardingJob.save() - those guards exist to stop rows disappearing
through ordinary UI/API use, not a deliberate admin re-seed like this one.

Idempotent: if the new definitions are already all present, this is a no-op,
so it is safe even if it somehow runs more than once on the same site.
"""

import frappe

NEW_DEFINITIONS = [
    ("PC_PREALERT_RECEIVED", "Pre-Alert Received", 1),
    ("PC_ENDORSEMENT_LETTER", "Endorsement Letter", 2),
    ("PC_COMMERCIAL_INVOICE", "Commercial Invoice", 3),
    ("PC_BILL_OF_LADING", "Bill of Lading", 4),
    ("PC_PACKING_LIST", "Packing List", 5),
    ("PC_SL_INVOICE_REQUESTED", "SL Invoice Requested", 6),
    ("PC_SL_INVOICE_RECEIVED", "SL Invoice Received", 7),
    ("PC_SL_INVOICE_PAID", "SL Invoice Paid", 8),
    ("PC_SL_BL_RELEASED", "SL BL Released", 9),
    ("PC_CUSTOMS_ENTRY_LODGED", "Customs Entry Lodged", 10),
    ("PC_CUSTOMS_CLEARANCE_COMPLETED", "Customs Clearance Completed", 11),
    ("PC_DO_REQUESTED", "DO Requested", 12),
    ("PC_DO_RECEIVED", "DO Received", 13),
    ("PC_PORT_RELEASE_LODGED", "Port Release Lodged", 14),
    ("PC_PORT_RELEASE_CONFIRMED", "Port Release Confirmed", 15),
]


def execute():
    if not frappe.db.exists("DocType", "Milestone Definition"):
        return

    new_codes = [code for code, _, _ in NEW_DEFINITIONS]
    already_applied = frappe.db.count(
        "Milestone Definition", {"milestone_code": ["in", new_codes]}
    ) == len(new_codes)
    if already_applied:
        return

    jobs = frappe.get_all(
        "Forwarding Job", filters={"requires_port_clearance": 1}, pluck="name"
    )

    # 1. Clear existing Port Clearance milestone rows on affected jobs first,
    # so deleting the old Milestone Definition docs below doesn't hit a
    # LinkExistsError.
    for job_name in jobs:
        frappe.db.delete(
            "Job Milestone Progress",
            {
                "parent": job_name,
                "parenttype": "Forwarding Job",
                "parentfield": "port_clearance_milestones",
            },
        )

    # 2. Delete every existing Port Clearance Milestone Definition.
    old_defs = frappe.get_all(
        "Milestone Definition", filters={"service_module": "Port Clearance"}, pluck="name"
    )
    for name in old_defs:
        frappe.delete_doc("Milestone Definition", name, ignore_permissions=True, force=True)

    # 3. Create the new definitions.
    new_defs = []
    for code, label, sequence in NEW_DEFINITIONS:
        doc = frappe.get_doc({
            "doctype": "Milestone Definition",
            "milestone_code": code,
            "milestone_label": label,
            "service_module": "Port Clearance",
            "direction": "Both",
            "sequence": sequence,
            "is_active": 1,
        }).insert(ignore_permissions=True)
        new_defs.append(doc)

    # 4. Rebuild the checklist (all unchecked) on every job with Port
    # Clearance enabled.
    for job_name in jobs:
        for idx, defn in enumerate(new_defs, 1):
            frappe.get_doc({
                "doctype": "Job Milestone Progress",
                "parent": job_name,
                "parenttype": "Forwarding Job",
                "parentfield": "port_clearance_milestones",
                "idx": idx,
                "milestone": defn.name,
                "milestone_code": defn.milestone_code,
                "milestone_label": defn.milestone_label,
                "service_module": "Port Clearance",
            }).insert(ignore_permissions=True)

    frappe.db.commit()
