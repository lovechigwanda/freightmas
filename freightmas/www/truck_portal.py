import frappe
from frappe.utils import now, today, get_datetime, format_datetime
from frappe import _


def get_context(context):
    job_name = frappe.form_dict.get("job")
    if not job_name:
        frappe.throw(_("Job ID is required."))

    doc = frappe.get_doc("Forwarding Job", job_name)

    if not doc.is_trucking_required:
        frappe.throw(_("This job does not require trucking services."))

    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to view this page."))

    total_cargo = len(doc.cargo_parcel_details)
    completed_cargo = sum(1 for cargo in doc.cargo_parcel_details if cargo.is_completed)
    pending_cargo = total_cargo - completed_cargo

    context.doc = doc
    context.total_cargo = total_cargo
    context.completed_cargo = completed_cargo
    context.pending_cargo = pending_cargo
    context.no_cache = 1
    return context


@frappe.whitelist()
def get_cargo_details(job, cargo_idx):
    """Get detailed cargo information for read-only display"""
    try:
        doc = frappe.get_doc("Forwarding Job", job)
        cargo_idx = int(cargo_idx)

        if cargo_idx < 0 or cargo_idx >= len(doc.cargo_parcel_details):
            frappe.throw(_("Invalid cargo index."))

        cargo = doc.cargo_parcel_details[cargo_idx]
        
        # Format dates properly
        def format_date(date_val):
            if not date_val:
                return ""
            return format_datetime(date_val, "dd-MMM-yy HH:mm") if hasattr(date_val, 'hour') else format_datetime(date_val, "dd-MMM-yy")

        return {
            "truck_details": {
                "transporter": cargo.transporter or "",
                "transporter_name": frappe.get_value("Supplier", cargo.transporter, "supplier_name") if cargo.transporter else "",
                "truck_reg_no": cargo.truck_reg_no or "",
                "trailer_reg_no": cargo.trailer_reg_no or "",
                "driver_name": cargo.driver_name or "",
                "driver_contact_no": cargo.driver_contact_no or "",
                "driver_contact_no_2": cargo.driver_contact_no_2 or "",
                "driver_passport_no": cargo.driver_passport_no or "",
                "driver_licence_no": cargo.driver_licence_no or "",
            },
            "tracking_info": {
                "truck_location": cargo.truck_location or "",
                "tracking_comment": cargo.tracking_comment or "",
                "updated_on": format_date(cargo.updated_on),
                "updated_by": cargo.updated_by or "",
                "load_by_date": format_date(cargo.load_by_date),
                "booked_on_date": format_date(cargo.booked_on_date),
                "loaded_on_date": format_date(cargo.loaded_on_date),
                "offloaded_on_date": format_date(cargo.offloaded_on_date),
                "returned_on_date": format_date(cargo.returned_on_date),
                "completed_on_date": format_date(cargo.completed_on_date),
            },
            "milestones": {
                "is_booked": cargo.is_booked or 0,
                "is_loaded": cargo.is_loaded or 0,
                "is_offloaded": cargo.is_offloaded or 0,
                "is_returned": cargo.is_returned or 0,
                "is_completed": cargo.is_completed or 0,
                "to_be_returned": cargo.to_be_returned or 0,
            }
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Cargo Details Error")
        frappe.throw(_("Failed to get cargo details: {0}").format(str(e)))


@frappe.whitelist()
def update_milestone(job, cargo_idx, milestone, date=None, comment=None, border_post=None):
    try:
        doc = frappe.get_doc("Forwarding Job", job)
        cargo_idx = int(cargo_idx)

        if cargo_idx < 0 or cargo_idx >= len(doc.cargo_parcel_details):
            frappe.throw(_("Invalid cargo index."))

        cargo = doc.cargo_parcel_details[cargo_idx]
        milestone_date = get_datetime(date) if date else today()

        # Milestone sequence validation
        validation_rules = {
            "booked": (cargo.truck_reg_no, "Assign truck first"),
            "loaded": (cargo.is_booked, "Cannot mark as Loaded before Booked"),
            "border1_arrived": (cargo.is_loaded, "Cannot mark Border Arrived before Loaded"),
            "border1_left": (cargo.border_arrived_on, "Cannot mark Border Left before Border Arrived"),
            "offload_arrived": (cargo.border_left_on, "Cannot mark Offloading Point before Border Left"),
            "offloaded": (cargo.offloading_arrived_on, "Cannot mark as Offloaded before Offloading Point"),
            "returned": (cargo.is_offloaded, "Cannot mark as Returned before Offloaded"),
            "completed": (
                cargo.is_returned if cargo.to_be_returned else cargo.is_offloaded,
                "Cannot mark as Completed before " + ("Returned" if cargo.to_be_returned else "Offloaded")
            ),
        }

        if milestone in validation_rules:
            is_valid, error_msg = validation_rules[milestone]
            if not is_valid:
                frappe.throw(_(error_msg))

        # Standard milestones
        milestone_map = {
            "booked": ("is_booked", "booked_on_date"),
            "loaded": ("is_loaded", "loaded_on_date"),
            "offloaded": ("is_offloaded", "offloaded_on_date"),
            "returned": ("is_returned", "returned_on_date"),
            "completed": ("is_completed", "completed_on_date"),
        }

        if milestone in milestone_map:
            flag_field, date_field = milestone_map[milestone]
            setattr(cargo, flag_field, 1)
            setattr(cargo, date_field, milestone_date)
        
        # Border 1 Arrived
        elif milestone == "border1_arrived":
            cargo.border_tracking = 1
            if border_post:
                cargo.border_name = border_post
            cargo.border_arrived_on = milestone_date
        
        # Border 1 Left
        elif milestone == "border1_left":
            cargo.border_left_on = milestone_date
        
        # Border 2 Arrived
        elif milestone == "border2_arrived":
            cargo.border_2_tracking = 1
            if border_post:
                cargo.border_2_name = border_post
            cargo.border_2_arrived_on = milestone_date
        
        # Border 2 Left
        elif milestone == "border2_left":
            cargo.border_2_left_on = milestone_date
        
        # Offloading point arrival
        elif milestone == "offload_arrived":
            cargo.offloading_point = 1
            cargo.offloading_arrived_on = milestone_date

        if comment:
            cargo.tracking_comment = comment

        cargo.updated_on = now()
        cargo.updated_by = frappe.session.user

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "message": _("Milestone updated successfully.")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Update Milestone Error")
        frappe.throw(_("Failed to update milestone: {0}").format(str(e)))


@frappe.whitelist()
def update_tracking(job, cargo_idx, truck_location=None, comment=None):
    try:
        doc = frappe.get_doc("Forwarding Job", job)
        cargo_idx = int(cargo_idx)

        if cargo_idx < 0 or cargo_idx >= len(doc.cargo_parcel_details):
            frappe.throw(_("Invalid cargo index."))

        cargo = doc.cargo_parcel_details[cargo_idx]

        if truck_location:
            cargo.truck_location = truck_location

        if comment:
            cargo.tracking_comment = comment

        cargo.updated_on = now()
        cargo.updated_by = frappe.session.user

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "message": _("Tracking updated successfully.")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Update Tracking Error")
        frappe.throw(_("Failed to update tracking: {0}").format(str(e)))


@frappe.whitelist()
def update_truck_details(
    job,
    cargo_idx,
    transporter=None,
    truck_reg_no=None,
    trailer_reg_no=None,
    driver_name=None,
    driver_contact_no=None,
    driver_contact_no_2=None,
    driver_passport_no=None,
    driver_licence_no=None,
):
    try:
        doc = frappe.get_doc("Forwarding Job", job)
        cargo_idx = int(cargo_idx)

        if cargo_idx < 0 or cargo_idx >= len(doc.cargo_parcel_details):
            frappe.throw(_("Invalid cargo index."))

        cargo = doc.cargo_parcel_details[cargo_idx]

        # Update all fields
        cargo.transporter = transporter or ""
        cargo.truck_reg_no = truck_reg_no or ""
        cargo.trailer_reg_no = trailer_reg_no or ""
        cargo.driver_name = driver_name or ""
        cargo.driver_contact_no = driver_contact_no or ""
        cargo.driver_contact_no_2 = driver_contact_no_2 or ""
        cargo.driver_passport_no = driver_passport_no or ""
        cargo.driver_licence_no = driver_licence_no or ""

        cargo.updated_on = now()
        cargo.updated_by = frappe.session.user

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "message": _("Truck details updated successfully.")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Update Truck Details Error")
        frappe.throw(_("Failed to update truck details: {0}").format(str(e)))


@frappe.whitelist()
def enable_trucking_for_cargo(job, cargo_idx):
    try:
        doc = frappe.get_doc("Forwarding Job", job)
        cargo_idx = int(cargo_idx)

        if cargo_idx < 0 or cargo_idx >= len(doc.cargo_parcel_details):
            frappe.throw(_("Invalid cargo index."))

        cargo = doc.cargo_parcel_details[cargo_idx]
        cargo.is_truck_required = 1
        cargo.updated_on = now()
        cargo.updated_by = frappe.session.user

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "message": _("Trucking enabled for this cargo.")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Enable Trucking Error")
        frappe.throw(_("Failed to enable trucking: {0}").format(str(e)))


@frappe.whitelist()
def update_extended_tracking(
    job,
    cargo_idx,
    border_arrived_on=None,
    border_left_on=None,
    offloading_arrived_on=None,
):
    """Update extended tracking fields (border crossing, offloading point)"""
    try:
        doc = frappe.get_doc("Forwarding Job", job)
        cargo_idx = int(cargo_idx)

        if cargo_idx < 0 or cargo_idx >= len(doc.cargo_parcel_details):
            frappe.throw(_("Invalid cargo index."))

        cargo = doc.cargo_parcel_details[cargo_idx]

        # Update border tracking
        if border_arrived_on:
            cargo.border_arrived_on = get_datetime(border_arrived_on)
        if border_left_on:
            cargo.border_left_on = get_datetime(border_left_on)

        # Update offloading point tracking
        if offloading_arrived_on:
            cargo.offloading_arrived_on = get_datetime(offloading_arrived_on)

        cargo.updated_on = now()
        cargo.updated_by = frappe.session.user

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "message": _("Extended tracking updated successfully.")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Update Extended Tracking Error")
        frappe.throw(_("Failed to update extended tracking: {0}").format(str(e)))


@frappe.whitelist()
def add_job_tracking(job, comment):
    """Add a job-level tracking comment"""
    try:
        doc = frappe.get_doc("Forwarding Job", job)
        
        # Add to the tracking table
        doc.append("forwarding_tracking", {
            "comment": comment,
            "updated_by": frappe.session.user,
            "updated_on": now()
        })
        
        # Update the current comment fields
        doc.current_comment = comment
        doc.last_updated_by = frappe.session.user
        doc.last_updated_on = now()
        
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "message": _("Tracking added successfully.")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Add Job Tracking Error")
        frappe.throw(_("Failed to add tracking: {0}").format(str(e)))
