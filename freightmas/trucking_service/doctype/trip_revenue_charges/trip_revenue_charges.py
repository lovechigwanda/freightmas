# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TripRevenueCharges(Document):
	pass


######################################################

import frappe

def before_delete(doc, method):
    """
    Prevent deletion of invoiced charges at the server level.
    """
    if doc.is_invoiced or doc.sales_invoice:
        frappe.throw(
            f"Cannot delete charge '{doc.charge}' because it has been invoiced. Associated Invoice: {doc.sales_invoice or 'N/A'}."
        )


##########################################################

