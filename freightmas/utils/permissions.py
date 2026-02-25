# FreightMas Permission Utilities
# Centralised security helpers for API endpoints and portal access.

import frappe
from frappe import _


FREIGHTMAS_ROLES = ("FreightMas User", "FreightMas Manager", "System Manager", "Administrator")


def check_freightmas_role():
    """Verify the current user holds at least one FreightMas role.

    Raises:
        frappe.PermissionError: If the user does not have any of the required roles.
    """
    roles = frappe.get_roles(frappe.session.user)
    if not any(r in roles for r in FREIGHTMAS_ROLES):
        frappe.throw(
            _("You do not have permission to perform this action."),
            frappe.PermissionError,
        )


def check_doc_read_permission(doctype, docname):
    """Verify the current user has read permission on a specific document.

    This is the standard gate for invoice-creation and similar endpoints:
    if a user can see the source document, they may create invoices from it.

    Args:
        doctype (str): The DocType name (e.g. "Trip", "Clearing Job").
        docname (str): The document name/ID.

    Raises:
        frappe.PermissionError: If the user lacks read access to the document.
    """
    frappe.has_permission(doctype, "read", docname, throw=True)
