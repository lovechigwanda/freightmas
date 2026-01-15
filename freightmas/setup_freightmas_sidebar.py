"""
Script to create FreightMas parent Workspace Sidebar with all modules as children
Run with: bench --site <sitename> execute freightmas.setup_freightmas_sidebar.setup
"""
import frappe

def setup():
    """Create FreightMas parent sidebar and remove individual service sidebars"""
    
    # Define the child workspaces for FreightMas (only existing workspaces)
    child_workspaces = [
        {"label": "Home", "link_to": "Port Clearing Service"},
        {"label": "Port Clearing", "link_to": "Port Clearing Service"},
        {"label": "Trucking", "link_to": "Trucking Service"},
        {"label": "Forwarding", "link_to": "Forwarding Service"},
        {"label": "Road Freight", "link_to": "Road Freight Service"},
        {"label": "FreightMas Accounts", "link_to": "FreightMas Accounts"},
    ]
    
    # Individual sidebars to delete (will be grouped under FreightMas)
    sidebars_to_delete = [
        "Port Clearing Service",
        "Trucking Service",
        "Forwarding Service",
        "Road Freight Service",
        "FreightMas Accounts",
    ]
    
    # Create the parent FreightMas Workspace Sidebar
    if frappe.db.exists("Workspace Sidebar", "FreightMas"):
        frappe.delete_doc("Workspace Sidebar", "FreightMas", force=True)
    
    freightmas_sidebar = frappe.new_doc("Workspace Sidebar")
    freightmas_sidebar.name = "FreightMas"
    freightmas_sidebar.title = "FreightMas"
    freightmas_sidebar.header_icon = "truck"
    freightmas_sidebar.standard = 1
    freightmas_sidebar.app = "freightmas"
    
    # Add child workspace items
    for idx, ws in enumerate(child_workspaces, start=1):
        freightmas_sidebar.append("items", {
            "idx": idx,
            "label": ws["label"],
            "link_type": "Workspace",
            "link_to": ws["link_to"],
            "type": "Link",
            "child": 0,
        })
    
    freightmas_sidebar.insert(ignore_permissions=True)
    print(f"✅ Created FreightMas parent sidebar with {len(child_workspaces)} modules")
    
    # Delete individual service sidebars
    for sidebar_name in sidebars_to_delete:
        if frappe.db.exists("Workspace Sidebar", sidebar_name):
            frappe.delete_doc("Workspace Sidebar", sidebar_name, force=True)
            print(f"🗑️  Deleted individual sidebar: {sidebar_name}")
    
    frappe.db.commit()
    print("\n🎉 FreightMas sidebar setup complete!")
    print("   Refresh your browser to see the changes.")

if __name__ == "__main__":
    setup()
