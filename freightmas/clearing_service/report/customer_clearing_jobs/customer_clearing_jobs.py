# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, getdate, formatdate
from frappe.utils.pdf import get_pdf

def fmt(date_val):
    if not date_val:
        return "-"
    return formatdate(date_val, "dd-MMM-yy")

def calculate_dnd_storage_days_import(job, cont):
    to_be_returned = int(getattr(cont, "to_be_returned", 0) or 0)
    is_loaded = int(getattr(cont, "is_loaded", 0) or 0)
    is_returned = int(getattr(cont, "is_returned", 0) or 0)
    gate_in_empty_date = getdate(getattr(cont, "gate_in_empty_date", None))
    gate_out_full_date = getdate(getattr(cont, "gate_out_full_date", None))
    discharge_date = getdate(getattr(job, "discharge_date", None))
    dnd_free_days = int(getattr(job, "dnd_free_days", 0) or 0)
    port_free_days = int(getattr(job, "port_free_days", 0) or 0)
    today_dt = getdate(nowdate())

    # DND end date logic
    if to_be_returned:
        if is_loaded and is_returned and gate_in_empty_date:
            dnd_end_date = gate_in_empty_date
        else:
            dnd_end_date = today_dt
    else:
        if is_loaded and gate_out_full_date:
            dnd_end_date = gate_out_full_date
        else:
            dnd_end_date = today_dt

    # Storage end date logic
    if not is_loaded:
        storage_end_date = today_dt
    elif is_loaded and gate_out_full_date:
        storage_end_date = gate_out_full_date
    else:
        storage_end_date = today_dt

    # DND days
    if dnd_end_date and discharge_date:
        dnd_days = (dnd_end_date - discharge_date).days - dnd_free_days
        dnd_days = max(dnd_days, 0)
    else:
        dnd_days = 0

    # Storage days
    if storage_end_date and discharge_date:
        storage_days = (storage_end_date - discharge_date).days - port_free_days
        storage_days = max(storage_days, 0)
    else:
        storage_days = 0

    return dnd_days, storage_days

def calculate_dnd_storage_days_export(job, cont):
    pick_up_empty_date = getdate(getattr(cont, "pick_up_empty_date", None))
    gate_in_full_date = getdate(getattr(cont, "gate_in_full_date", None))
    loaded_on_vessel_date = getdate(getattr(cont, "loaded_on_vessel_date", None))
    is_loaded_on_vessel = int(getattr(cont, "is_loaded_on_vessel", 0) or 0)
    dnd_free_days = int(getattr(job, "dnd_free_days", 0) or 0)
    port_free_days = int(getattr(job, "port_free_days", 0) or 0)
    today_dt = getdate(nowdate())

    # DND and Storage end date logic for exports
    end_date = loaded_on_vessel_date if is_loaded_on_vessel and loaded_on_vessel_date else today_dt

    # DND days: from pick_up_empty_date to end_date
    if pick_up_empty_date:
        dnd_days = (end_date - pick_up_empty_date).days - dnd_free_days
        dnd_days = max(dnd_days, 0)
    else:
        dnd_days = 0

    # Storage days: from gate_in_full_date to end_date
    if gate_in_full_date:
        storage_days = (end_date - gate_in_full_date).days - port_free_days
        storage_days = max(storage_days, 0)
    else:
        storage_days = 0

    return dnd_days, storage_days

def fetch_clearing_jobs(customer, direction=None, bl_number=None):
    filters = {"customer": customer}
    if direction:
        filters["direction"] = direction
    if bl_number:
        filters["bl_number"] = bl_number

    jobs = []
    job_names = frappe.get_all(
        "Clearing Job",
        filters=filters,
        fields=["name", "status", "completed_on", "date_created", "cargo_count", "eta", "etd", "bl_number"],
        order_by="date_created desc"
    )
    today = getdate(nowdate())
    for j in job_names:
        doc = frappe.get_doc("Clearing Job", j.name)
        # Only include jobs not completed or completed in last 7 days
        if doc.status != "Completed" or (
            doc.status == "Completed" and doc.completed_on and (today - getdate(doc.completed_on)).days <= 7
        ):
            # Milestones: group by direction and order as per requirements
            if doc.direction == "Import":
                milestones = [
                    ("Is BL Received", doc.is_bl_received, fmt(doc.bl_received_date)),
                    ("Is BL Confirmed", doc.is_bl_confirmed, fmt(doc.bl_confirmed_date)),
                    ("Is Vessel Arrived at Port", doc.is_vessel_arrived_at_port, fmt(doc.vessel_arrived_date)),
                    ("Is SL Invoice Received", doc.is_sl_invoice_received, fmt(doc.sl_invoice_received_date)),
                    ("Is SL Invoice Paid", doc.is_sl_invoice_paid, fmt(doc.sl_invoice_payment_date)),
                    ("Is Discharged from Vessel", doc.is_discharged_from_vessel, fmt(doc.discharge_date)),
                    ("Is DO Requested", doc.is_do_requested, fmt(doc.do_requested_date)),
                    ("Is DO Received", doc.is_do_received, fmt(doc.do_received_date)),
                    ("Is Port Release Confirmed", doc.is_port_release_confirmed, fmt(doc.port_release_confirmed_date)),
                    ("Is Discharged from Port", doc.is_discharged_from_port, fmt(doc.date_discharged_from_port)),
                ]
            else:  # Export
                milestones = [
                    ("Is Booking Confirmed", doc.is_booking_confirmed, fmt(doc.booking_confirmation_date)),
                    ("Is Clearing for Shipment Done", doc.is_clearing_for_shipment_done, fmt(doc.shipment_cleared_date)),
                    ("Is Loaded on Vessel", doc.is_loaded_on_vessel, fmt(doc.loaded_on_vessel_date)),
                    ("Is Vessel Sailed", doc.is_vessel_sailed, fmt(doc.vessel_sailed_date)),
                ]

            # Containerised and General Cargo separation
            containers = []
            general_cargo = []
            for c in doc.cargo_package_details:
                if c.cargo_type == "Containerised":
                    if doc.direction == "Import":
                        dnd_days, storage_days = calculate_dnd_storage_days_import(doc, c)
                        containers.append({
                            "container_number": c.container_number,
                            "container_type": c.container_type,
                            "gate_out_full_date": fmt(c.gate_out_full_date),
                            "gate_in_empty_date": fmt(c.gate_in_empty_date),
                            "dnd_days": dnd_days,
                            "storage_days": storage_days,
                            "direction": doc.direction,
                        })
                    else:  # Export
                        dnd_days, storage_days = calculate_dnd_storage_days_export(doc, c)
                        containers.append({
                            "container_number": c.container_number,
                            "container_type": c.container_type,
                            "pick_up_empty_date": fmt(c.pick_up_empty_date),
                            "gate_in_full_date": fmt(c.gate_in_full_date),
                            "loaded_on_vessel_date": fmt(c.loaded_on_vessel_date),
                            "dnd_days": dnd_days,
                            "storage_days": storage_days,
                            "direction": doc.direction,
                        })
                elif c.cargo_type == "General Cargo":
                    if doc.direction == "Import":
                        dnd_days, storage_days = calculate_dnd_storage_days_import(doc, c)
                        general_cargo.append({
                            "cargo_item_description": c.cargo_item_description,
                            "cargo_quantity": c.cargo_quantity,
                            "cargo_uom": c.cargo_uom,
                            "gate_out_full_date": fmt(c.gate_out_full_date),
                            "gate_in_empty_date": fmt(c.gate_in_empty_date),
                            "dnd_days": dnd_days,
                            "storage_days": storage_days,
                            "direction": doc.direction,
                        })
                    else:  # Export
                        dnd_days, storage_days = calculate_dnd_storage_days_export(doc, c)
                        general_cargo.append({
                            "cargo_item_description": c.cargo_item_description,
                            "cargo_quantity": c.cargo_quantity,
                            "cargo_uom": c.cargo_uom,
                            "pick_up_empty_date": fmt(c.pick_up_empty_date),
                            "gate_in_full_date": fmt(c.gate_in_full_date),
                            "loaded_on_vessel_date": fmt(c.loaded_on_vessel_date),
                            "dnd_days": dnd_days,
                            "storage_days": storage_days,
                            "direction": doc.direction,
                        })

            jobs.append({
                "name": doc.name,
                "date_created": fmt(doc.date_created),
                "direction": doc.direction,
                "bl_number": doc.bl_number,
                "status": doc.status,
                "completed_on": fmt(getattr(doc, "completed_on", None)),
                "cargo_count": getattr(doc, "cargo_count", ""),
                "eta": fmt(getattr(doc, "eta", None)),
                "etd": fmt(getattr(doc, "etd", None)),
                "milestones": milestones,
                "containers": containers,
                "general_cargo": general_cargo,
                "current_comment": getattr(doc, "current_comment", ""),
                "last_updated_on": fmt(getattr(doc, "last_updated_on", None)),
            })
    return jobs

def get_report_context(customer, direction=None, bl_number=None):
    company = frappe.defaults.get_global_default("company")
    customer_doc = frappe.get_doc("Customer", customer)
    jobs = fetch_clearing_jobs(customer, direction, bl_number)
    return {
        "company": company,
        "customer_name": customer_doc.customer_name,
        "jobs": jobs,
        "export_date": frappe.utils.formatdate(nowdate(), "dd-MMM-yy"),
        "report_title": "Customer Clearing Jobs Report"
    }

@frappe.whitelist()
def export_customer_clearing_jobs_pdf(customer, direction=None, bl_number=None):
    context = get_report_context(customer, direction, bl_number)
    html = frappe.render_template(
        "freightmas/clearing_service/report/customer_clearing_jobs/customer_clearing_jobs_pdf.html",
        context
    )
    pdf_bytes = get_pdf(html)
    frappe.response.filename = "Customer_Clearing_Jobs.pdf"
    frappe.response.filecontent = pdf_bytes
    frappe.response.type = "download"

def execute(filters=None):
    filters = filters or {}
    customer = filters.get("customer")
    direction = filters.get("direction")
    bl_number = filters.get("bl_number")
    jobs = fetch_clearing_jobs(customer, direction, bl_number)

    # Define columns for the report view (adjust as needed)
    columns = [
        {"label": "Job Number", "fieldname": "name", "fieldtype": "Data", "width": 120},
        {"label": "Date Created", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 80},
        {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Completed On", "fieldname": "completed_on", "fieldtype": "Data", "width": 100},
        {"label": "Cargo", "fieldname": "cargo_count", "fieldtype": "Data", "width": 80},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 100},
        {"label": "ETD", "fieldname": "etd", "fieldtype": "Data", "width": 100},
    ]

    # Flatten jobs for the report view (one row per job)
    data = []
    for job in jobs:
        data.append({
            "name": job["name"],
            "date_created": job["date_created"],
            "direction": job["direction"],
            "bl_number": job["bl_number"],
            "status": job["status"],
            "completed_on": job["completed_on"],
            "cargo_count": job["cargo_count"],
            "eta": job["eta"],
            "etd": job["etd"],
        })

    return columns, data