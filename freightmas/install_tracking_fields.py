#!/usr/bin/env python3

import frappe

def create_tracking_email_fields():
    """Create custom fields for customer tracking emails"""
    
    custom_fields = [
        {
            "doctype": "Custom Field",
            "dt": "Customer",
            "fieldname": "tracking_email_settings_section",
            "label": "Tracking Email Settings",
            "fieldtype": "Section Break",
            "insert_after": "email_id",
            "collapsible": 1
        },
        {
            "doctype": "Custom Field",
            "dt": "Customer",
            "fieldname": "tracking_email",
            "label": "Primary Tracking Email",
            "fieldtype": "Data",
            "options": "Email",
            "insert_after": "tracking_email_settings_section",
            "description": "Primary email address for tracking reports and notifications"
        },
        {
            "doctype": "Custom Field",
            "dt": "Customer",
            "fieldname": "tracking_cc_emails",
            "label": "CC Recipients",
            "fieldtype": "Small Text",
            "insert_after": "tracking_email",
            "description": "Additional email addresses to CC (comma-separated)"
        },
        {
            "doctype": "Custom Field",
            "dt": "Customer",
            "fieldname": "tracking_email_enabled",
            "label": "Enable Tracking Emails",
            "fieldtype": "Check",
            "default": "1",
            "insert_after": "tracking_cc_emails",
            "description": "Allow sending tracking reports to this customer via email"
        }
    ]
    
    for field_data in custom_fields:
        # Check if field already exists
        if not frappe.db.exists("Custom Field", {"dt": field_data["dt"], "fieldname": field_data["fieldname"]}):
            try:
                custom_field = frappe.get_doc(field_data)
                custom_field.insert()
                print(f"✅ Created field: {field_data['fieldname']}")
            except Exception as e:
                print(f"❌ Error creating {field_data['fieldname']}: {str(e)}")
        else:
            print(f"⏭️  Field already exists: {field_data['fieldname']}")
    
    # Clear cache to refresh forms
    frappe.clear_cache()
    print("🔄 Cache cleared - fields should now be visible!")

if __name__ == "__main__":
    frappe.init()
    frappe.connect()
    create_tracking_email_fields()