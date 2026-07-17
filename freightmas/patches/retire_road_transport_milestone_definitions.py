# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe

# Road Transport milestones (RT_BOOKED/RT_LOADED/RT_OFFLOADED/RT_RETURNED) are
# redundant with the per-container/parcel tracking already captured on
# cargo_parcel_details (is_booked/is_loaded/is_offloaded/is_returned). The
# Forwarding Job Milestones tab now shows a read-only rollup of that data
# instead (road_transport_progress_summary), so these definitions are retired
# rather than deleted (preserves any historical Job Milestone Progress rows
# that already reference them).
RETIRED_CODES = ["RT_BOOKED", "RT_LOADED", "RT_OFFLOADED", "RT_RETURNED"]


def execute():
    if not frappe.db.exists("DocType", "Milestone Definition"):
        return

    for code in RETIRED_CODES:
        name = frappe.db.get_value("Milestone Definition", {"milestone_code": code}, "name")
        if name:
            frappe.db.set_value("Milestone Definition", name, "is_active", 0)

    frappe.db.commit()
