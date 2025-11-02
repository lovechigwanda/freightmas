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
    
    # Check if trucking is required instead of share_with_road_freight
    if not doc.is_trucking_required:
        frappe.throw("This job does not require trucking services")
    
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
    
    # Check if trucking is required instead of share_with_road_freight
    if not doc.is_trucking_required:
        frappe.throw(_("This job does not require trucking services"))
    
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
    
    # ✅ SEND EMAIL - Only for new bookings
    send_email_notification(
        doc=doc,
        cargo=cargo,
        subject=f"New Truck Booking - {doc.name}",
        message=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h2 style="margin: 0;">🚛 New Truck Booking</h2>
                </div>
                <div style="background: white; padding: 30px; border: 1px solid #e0e6ed; border-radius: 0 0 8px 8px;">
                    <p><strong>Job:</strong> {doc.name}</p>
                    <p><strong>Container/Cargo:</strong> {cargo.container_number or cargo.cargo_item_description}</p>
                    
                    <div style="background: #f8f9fb; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Booking Details</h3>
                        <p><strong>🏢 Transporter:</strong> {transporter}</p>
                        <p><strong>🚚 Truck:</strong> {truck_reg_no}</p>
                        <p><strong>👤 Driver:</strong> {driver_name}</p>
                        <p><strong>📞 Contact:</strong> {driver_contact_no}</p>
                    </div>
                    
                    <p style="background: #fef3c7; padding: 12px; border-left: 4px solid #f59e0b; border-radius: 4px;">
                        <strong>⚠️ Action Required:</strong> Please review and approve this booking.
                    </p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{frappe.utils.get_url()}/truck_portal?job={doc.name}" 
                           style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block;">
                            View Portal
                        </a>
                    </div>
                </div>
            </div>
        """
    )
    
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
    
    # ❌ NO EMAIL - Too frequent
    
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
    
    # ❌ NO EMAIL - Rejection is final, user is already on portal
    
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
    
    # ❌ NO EMAIL - Internal status change
    
    return {"success": True}


@frappe.whitelist()
def update_tracking(job, cargo_idx, status, location, comment):
    """Update truck tracking"""
    
    # Get document
    doc = frappe.get_doc("Forwarding Job", job)
    
    # Check if trucking is required instead of share_with_road_freight
    if not doc.is_trucking_required:
        frappe.throw(_("This job does not require trucking services"))
    
    # Get cargo row
    cargo_idx = int(cargo_idx)
    cargo = doc.cargo_parcel_details[cargo_idx]
    
    # Store previous status
    previous_status = cargo.booking_status
    
    # Update tracking
    cargo.booking_status = status
    cargo.truck_location = location
    cargo.tracking_comment = comment
    cargo.updated_on = now()
    cargo.updated_by = frappe.session.user
    
    # Save
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    # ✅ SEND EMAIL - Only when delivered (final status)
    if status == "Delivered" and previous_status != "Delivered":
        send_email_notification(
            doc=doc,
            cargo=cargo,
            subject=f"✅ Delivery Complete - {doc.name}",
            message=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                        <h2 style="margin: 0;">✅ Cargo Delivered</h2>
                    </div>
                    <div style="background: white; padding: 30px; border: 1px solid #e0e6ed; border-radius: 0 0 8px 8px;">
                        <p><strong>Job:</strong> {doc.name}</p>
                        <p><strong>Container/Cargo:</strong> {cargo.container_number or cargo.cargo_item_description}</p>
                        
                        <div style="background: #d1fae5; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #10b981;">
                            <h3 style="margin-top: 0; color: #065f46;">Final Status</h3>
                            <p><strong>📍 Location:</strong> {location}</p>
                            <p><strong>💬 Comment:</strong> {comment}</p>
                            <p><strong>🚚 Truck:</strong> {cargo.truck_reg_no or '-'}</p>
                            <p><strong>👤 Driver:</strong> {cargo.driver_name or '-'}</p>
                        </div>
                        
                        <div style="text-align: center; margin-top: 30px;">
                            <a href="{frappe.utils.get_url()}/truck_portal?job={doc.name}" 
                               style="background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block;">
                                View Details
                            </a>
                        </div>
                    </div>
                </div>
            """
        )
    
    return {"success": True}


# ========================================================
# HELPER FUNCTION - EMAIL NOTIFICATION
# ========================================================

def send_email_notification(doc, cargo, subject, message):
    """Send email notification to job owner only"""
    
    try:
        # Only send to job owner
        frappe.sendmail(
            recipients=[doc.owner],
            subject=subject,
            message=message,
            now=True  # Send immediately
        )
    except Exception as e:
        # Log error but don't fail the transaction
        frappe.log_error(
            message=f"Email notification failed: {str(e)}",
            title=f"Truck Portal Email Error - {doc.name}"
        )