# Client Portal dashboard overview - shipment KPIs only.
#
# Invoice/payment KPIs land in Phase 2 once freightmas/portal/api/invoices.py
# and payments.py exist; the frontend renders placeholder tiles for those
# until then rather than this endpoint guessing at their shape.

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from freightmas.portal.api.shipments import JOB_LIST_FIELDS, NOT_ACTIVE_STATUSES
from freightmas.portal.security import check_portal_access, get_portal_customer_names, log_portal_access


@frappe.whitelist()
def get_overview():
	check_portal_access()
	customers = get_portal_customer_names()
	if not customers:
		frappe.throw(
			_("Your account is not linked to a customer profile. Contact your account manager."),
			frappe.PermissionError,
		)

	base_filters = {"docstatus": ["<", 2], "customer": ["in", customers]}

	active_count = frappe.db.count(
		"Forwarding Job", {**base_filters, "status": ["not in", NOT_ACTIVE_STATUSES]}
	)
	in_transit_count = frappe.db.count("Forwarding Job", {**base_filters, "status": "In Progress"})

	# get_all(), not get_list(): see the comment in portal/api/shipments.py -
	# Customer Portal User has zero DocType permissions by design.
	recent_jobs = frappe.get_all(
		"Forwarding Job",
		filters=base_filters,
		fields=JOB_LIST_FIELDS,
		order_by="modified desc",
		limit_page_length=5,
	)

	today = getdate(nowdate())
	overdue_count = 0
	for j in frappe.get_all(
		"Forwarding Job",
		filters={**base_filters, "status": ["not in", NOT_ACTIVE_STATUSES]},
		fields=["name", "direction", "eta", "ata", "etd", "atd"],
	):
		if (j.direction == "Import" and j.eta and getdate(j.eta) < today and not j.ata) or (
			j.direction == "Export" and j.etd and getdate(j.etd) < today and not j.atd
		):
			overdue_count += 1

	log_portal_access("view_dashboard", customer=customers[0] if len(customers) == 1 else None)

	return {
		"active_shipments": active_count,
		"in_transit": in_transit_count,
		"overdue": overdue_count,
		"recent_jobs": recent_jobs,
	}
