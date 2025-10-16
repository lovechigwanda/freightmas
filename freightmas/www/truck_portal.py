import frappe
from frappe.utils import now
from frappe import _

def get_context(context):
    """
    This function runs when someone accesses /truck_portal?job=FWJB-00001-25
    """
    
    # Get job name from URL parameter
    job_name = frappe.form_dict.get('job')
    
    if not job_name:
        frappe.throw("Job ID is required")
    
    # Get the Forwarding Job document
    try:
        doc = frappe.get_doc("Forwarding Job", job_name)
    except frappe.DoesNotExistError:
        frappe.throw(f"Forwarding Job {job_name} not found")
    
    # Check if it's shared
    if not doc.share_with_road_freight:
        frappe.throw("This job is not shared for web access")
    
    # Check permissions (basic - only logged in users)
    if frappe.session.user == "Guest":
        frappe.throw("Please login to view this page")
    
    # Pass document to template
    context.doc = doc
    context.no_cache = 1
    
    return context


# ========================================================
# API METHODS FOR TRUCK BOOKING PORTAL
# ========================================================

@frappe.whitelist()
def add_truck_booking(job, cargo_idx, transporter, truck_reg_no, trailer_reg_no=None,
                      driver_name=None, driver_contact_no=None, driver_passport_no=None,
                      driver_licence_no=None):
    """Add truck booking from web portal"""
    
    # Get document
    doc = frappe.get_doc("Forwarding Job", job)
    
    # Check if shared
    if not doc.share_with_road_freight:
        frappe.throw(_("This job is not shared for booking"))
    
    # Get cargo row
    cargo_idx = int(cargo_idx)
    if cargo_idx >= len(doc.cargo_parcel_details):
        frappe.throw(_("Invalid cargo index"))
    
    cargo = doc.cargo_parcel_details[cargo_idx]
    
    # Update fields
    cargo.transporter = transporter
    cargo.truck_reg_no = truck_reg_no
    cargo.trailer_reg_no = trailer_reg_no
    cargo.driver_name = driver_name
    cargo.driver_contact_no = driver_contact_no
    cargo.driver_passport_no = driver_passport_no
    cargo.driver_licence_no = driver_licence_no
    cargo.booking_status = "Pending"
    cargo.updated_on = now()
    cargo.updated_by = frappe.session.user
    
    # Save
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    # Send notification
    try:
        frappe.sendmail(
            recipients=[doc.owner],
            subject=f"New Truck Booking - {doc.name}",
            message=f"""
                <p>A new truck booking has been added for {cargo.container_number or cargo.cargo_item_description}</p>
                <p><strong>Transporter:</strong> {transporter}</p>
                <p><strong>Truck:</strong> {truck_reg_no}</p>
                <p><strong>Driver:</strong> {driver_name}</p>
                <p><a href="{frappe.utils.get_url()}/truck_portal?job={doc.name}">View Details</a></p>
            """
        )
    except Exception as e:
        frappe.log_error(f"Email notification failed: {str(e)}")
    
    return {"success": True, "message": _("Booking added successfully")}


@frappe.whitelist()
def approve_booking(job, cargo_idx):
    """Approve truck booking"""
    
    # Get document
    doc = frappe.get_doc("Forwarding Job", job)
    
    # Check permission (only owner can approve)
    if doc.owner != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the job owner can approve bookings"))
    
    # Get cargo row
    cargo_idx = int(cargo_idx)
    cargo = doc.cargo_parcel_details[cargo_idx]
    
    # Update status
    cargo.booking_status = "Approved"
    cargo.updated_on = now()
    cargo.updated_by = frappe.session.user
    
    # Save
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {"success": True}


@frappe.whitelist()
def reject_booking(job, cargo_idx, reason):
    """Reject truck booking"""
    
    # Get document
    doc = frappe.get_doc("Forwarding Job", job)
    
    # Check permission
    if doc.owner != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the job owner can reject bookings"))
    
    # Get cargo row
    cargo_idx = int(cargo_idx)
    cargo = doc.cargo_parcel_details[cargo_idx]
    
    # Update status
    cargo.booking_status = "Rejected"
    cargo.tracking_comment = f"Rejected: {reason}"
    cargo.updated_on = now()
    cargo.updated_by = frappe.session.user
    
    # Save
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {"success": True}


@frappe.whitelist()
def mark_booked(job, cargo_idx):
    """Mark truck as booked (ready for loading)"""
    
    # Get document
    doc = frappe.get_doc("Forwarding Job", job)
    
    # Check permission
    if doc.owner != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the job owner can mark as booked"))
    
    # Get cargo row
    cargo_idx = int(cargo_idx)
    cargo = doc.cargo_parcel_details[cargo_idx]
    
    # Update status
    cargo.booking_status = "Booked"
    cargo.updated_on = now()
    cargo.updated_by = frappe.session.user
    
    # Save
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {"success": True}


@frappe.whitelist()
def update_tracking(job, cargo_idx, status, location, comment):
    """Update truck tracking"""
    
    # Get document
    doc = frappe.get_doc("Forwarding Job", job)
    
    # Check if shared
    if not doc.share_with_road_freight:
        frappe.throw(_("This job is not shared"))
    
    # Get cargo row
    cargo_idx = int(cargo_idx)
    cargo = doc.cargo_parcel_details[cargo_idx]
    
    # Update tracking
    cargo.booking_status = status
    cargo.truck_location = location
    cargo.tracking_comment = comment
    cargo.updated_on = now()
    cargo.updated_by = frappe.session.user
    
    # Save
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    # Send notification to owner
    try:
        frappe.sendmail(
            recipients=[doc.owner],
            subject=f"Tracking Update - {doc.name}",
            message=f"""
                <p><strong>Status:</strong> {status}</p>
                <p><strong>Location:</strong> {location}</p>
                <p><strong>Comment:</strong> {comment}</p>
                <p><strong>Container/Cargo:</strong> {cargo.container_number or cargo.cargo_item_description}</p>
                <p><a href="{frappe.utils.get_url()}/truck_portal?job={doc.name}">View Details</a></p>
            """
        )
    except Exception as e:
        frappe.log_error(f"Email notification failed: {str(e)}")
    
    return {"success": True}