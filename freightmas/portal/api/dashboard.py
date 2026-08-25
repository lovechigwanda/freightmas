# Client Portal dashboard overview - shipment + billing KPIs.

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from freightmas.portal.api.shipments import JOB_LIST_FIELDS
from freightmas.portal.security import check_portal_access, get_portal_customer_names, log_portal_access
from freightmas.forwarding_service.utils.operational_phase import build_overview_phase_pipeline


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

	phase_pipeline = build_overview_phase_pipeline(customers=customers)

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

	invoice_filters = {"docstatus": 1, "customer": ["in", customers], "outstanding_amount": [">", 0]}
	outstanding_amount = (
		frappe.get_all(
			"Sales Invoice", filters=invoice_filters, fields=[{"SUM": "outstanding_amount", "as": "total"}]
		)[0].total
		or 0
	)
	overdue_amount = (
		frappe.get_all(
			"Sales Invoice",
			filters={**invoice_filters, "due_date": ["<", today]},
			fields=[{"SUM": "outstanding_amount", "as": "total"}],
		)[0].total
		or 0
	)

	log_portal_access("view_dashboard", customer=customers[0] if len(customers) == 1 else None)

	return {
		"phase_pipeline": phase_pipeline,
		"recent_jobs": recent_jobs,
		"outstanding_amount": outstanding_amount,
		"overdue_amount": overdue_amount,
	}
