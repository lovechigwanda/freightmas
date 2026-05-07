# FreightMas Permission Utilities
# Centralised security helpers for API endpoints and portal access.

import frappe
from frappe import _


FREIGHTMAS_ROLES = ("FreightMas User", "FreightMas Manager", "System Manager", "Administrator")


def check_freightmas_role(role=None):
    """Verify the current user holds a FreightMas role or a specific role.

    Args:
        role (str, optional): A specific role to require.

    Raises:
        frappe.PermissionError: If the user does not have the required role.
    """
    roles = frappe.get_roles(frappe.session.user)

    if role:
        if role not in roles and not any(r in roles for r in ("System Manager", "Administrator")):
            frappe.throw(
                _("You do not have permission to perform this action."),
                frappe.PermissionError,
            )
        return

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
