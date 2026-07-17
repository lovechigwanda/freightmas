# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe

# Sea/Air Freight milestones (SEA_VESSEL_DEPARTED/SEA_VESSEL_ARRIVED/
# SEA_DISCHARGED/SEA_GATE_OUT/SEA_EMPTY_RETURNED) are redundant with the
# job-level shipment dates (atd/ata) and per-container dates (discharge_date/
# gate_out_date/empty_return_date) already on cargo_parcel_details - in fact
# these milestones were only ever auto-ticked FROM those same dates. The
# Forwarding Job Milestones tab now shows a read-only rollup of that data
# instead (sea_air_freight_progress_summary), so these definitions are
# retired rather than deleted (preserves any historical Job Milestone
# Progress rows that already reference them).
RETIRED_CODES = [
    "SEA_VESSEL_DEPARTED",
    "SEA_VESSEL_ARRIVED",
    "SEA_DISCHARGED",
    "SEA_GATE_OUT",
    "SEA_EMPTY_RETURNED",
]


def execute():
    if not frappe.db.exists("DocType", "Milestone Definition"):
        return

    for code in RETIRED_CODES:
        name = frappe.db.get_value("Milestone Definition", {"milestone_code": code}, "name")
        if name:
            frappe.db.set_value("Milestone Definition", name, "is_active", 0)

    frappe.db.commit()
