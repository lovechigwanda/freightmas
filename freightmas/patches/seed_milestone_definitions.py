# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe

# Starter set of milestones per service module. These are just the initial
# defaults - users can add, reword or retire (untick Is Active) any of these
# afterwards from the Milestone Definition list without touching code.
DEFAULT_MILESTONES = [
    # NOTE: No "Sea/Air Freight" milestones here by design - that tracking is
    # shipment-level (atd/ata) and per-container (discharge_date/gate_out_date/
    # empty_return_date on cargo_parcel_details), rolled up read-only on the
    # Forwarding Job Milestones tab instead of a duplicate job-level checklist.

    # Road Freight (international)
    ("RDF_DEPARTED_ORIGIN", "Departed Origin", "Road Freight", "Both", 1),
    ("RDF_BORDER_CROSSED", "Border Crossed", "Road Freight", "Both", 2),
    ("RDF_ARRIVED_DESTINATION", "Arrived Destination", "Road Freight", "Both", 3),

    # Port Clearance
    ("PC_VESSEL_ARRIVED", "Vessel Arrived at Port", "Port Clearance", "Import", 1),
    ("PC_BOOKING_CONFIRMED", "Booking Confirmed", "Port Clearance", "Export", 1),
    ("PC_SL_INVOICE_RECEIVED", "Shipping Line Invoice Received", "Port Clearance", "Import", 2),
    ("PC_SL_INVOICE_PAID", "Shipping Line Invoice Paid", "Port Clearance", "Import", 3),
    ("PC_AWAITING_DO", "Awaiting Delivery Order", "Port Clearance", "Import", 4),
    ("PC_DO_RECEIVED", "Delivery Order Received", "Port Clearance", "Import", 5),
    ("PC_PORT_RELEASE_CONFIRMED", "Port Release Confirmed", "Port Clearance", "Import", 6),
    ("PC_DISCHARGED_FROM_PORT", "Discharged from Port", "Port Clearance", "Import", 7),

    # NOTE: No "Road Transport" milestones here by design - that tracking is
    # per-container/parcel and lives on cargo_parcel_details (is_booked/
    # is_loaded/is_offloaded/is_returned), rolled up read-only on the
    # Forwarding Job Milestones tab instead of a duplicate job-level checklist.

    # Border Clearance
    ("BC_DOCS_RECEIVED", "Documents Received", "Border Clearance", "Both", 1),
    ("BC_ENTRY_LODGED", "Entry Lodged", "Border Clearance", "Both", 2),
    ("BC_DUTY_ASSESSED", "Duty Assessed", "Border Clearance", "Both", 3),
    ("BC_DUTY_PAID", "Duty Paid", "Border Clearance", "Both", 4),
    ("BC_RELEASE_OBTAINED", "Release Obtained", "Border Clearance", "Both", 5),

    # Warehouse
    ("WH_GOODS_RECEIVED", "Goods Received", "Warehouse", "Both", 1),
    ("WH_PUTAWAY_COMPLETE", "Putaway Complete", "Warehouse", "Both", 2),
    ("WH_READY_FOR_DISPATCH", "Ready for Dispatch", "Warehouse", "Both", 3),
    ("WH_DISPATCHED", "Dispatched", "Warehouse", "Both", 4),
]


def execute():
    if not frappe.db.exists("DocType", "Milestone Definition"):
        return

    for code, label, service_module, direction, sequence in DEFAULT_MILESTONES:
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

    frappe.db.commit()
