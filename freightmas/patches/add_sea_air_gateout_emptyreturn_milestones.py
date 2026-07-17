# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe

# Additional Sea/Air Freight milestones aligned to the DCSA/Searates event
# codes the tracking integration already parses (see
# integrations/tracking/searates.py: DISC, GOUT/GTOT/AVPU/DLVR, IRTN/EMRT/RTRN).
# Added after the initial seed_milestone_definitions patch, so this is a
# separate idempotent patch rather than editing the already-executed one.
NEW_MILESTONES = [
    ("SEA_GATE_OUT", "Gate Out / Available for Pickup", "Sea/Air Freight", "Both", 4),
    ("SEA_EMPTY_RETURNED", "Empty Container Returned", "Sea/Air Freight", "Both", 5),
]


def execute():
    if not frappe.db.exists("DocType", "Milestone Definition"):
        return

    for code, label, service_module, direction, sequence in NEW_MILESTONES:
        if frappe.db.exists("Milestone Definition", {"milestone_code": code}):
            continue

        frappe.get_doc({
            "doctype": "Milestone Definition",
            "milestone_code": code,
            "milestone_label": label,
            "service_module": service_module,
            "direction": direction,
            "sequence": sequence,
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Relabel SEA_DISCHARGED for consistency with the new set, if unchanged from the original seed
    discharged_name = frappe.db.get_value("Milestone Definition", {"milestone_code": "SEA_DISCHARGED"}, "name")
    if discharged_name:
        if frappe.db.get_value("Milestone Definition", discharged_name, "milestone_label") == "Discharged":
            frappe.db.set_value("Milestone Definition", discharged_name, "milestone_label", "Discharged from Vessel")

    frappe.db.commit()
