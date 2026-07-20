# Supplier Portal dashboard overview - job counts only.
#
# No cost/margin KPI tile here: a "total payable" figure is deferred to
# Phase 2's Purchase Invoice outstanding_amount, to avoid shipping two
# different "how much do you owe me" numbers (a job-charge-line sum here
# vs. an invoice-derived figure there) that could disagree and confuse a
# supplier.

import frappe

from freightmas.portal.security import SUPPLIER_PORTAL_ROLE, check_portal_access, log_portal_access
from freightmas.portal.supplier.jobs import DEFAULT_JOB_DOCTYPE, JOB_TYPE_FIELDS, _caller_supplier_filter
from freightmas.portal.supplier_scope import get_supplier_job_names

NOT_ACTIVE_STATUSES = ["Completed", "Closed", "Cancelled"]


@frappe.whitelist()
def get_overview():
	check_portal_access(role=SUPPLIER_PORTAL_ROLE)
	suppliers = _caller_supplier_filter()

	job_names = get_supplier_job_names(DEFAULT_JOB_DOCTYPE, suppliers)

	base_filters = {"name": ["in", job_names], "docstatus": ["<", 2]}
	active_count = frappe.db.count(
		DEFAULT_JOB_DOCTYPE, {**base_filters, "status": ["not in", NOT_ACTIVE_STATUSES]}
	) if job_names else 0

	recent_jobs = (
		frappe.get_all(
			DEFAULT_JOB_DOCTYPE,
			filters=base_filters,
			fields=JOB_TYPE_FIELDS[DEFAULT_JOB_DOCTYPE],
			order_by="modified desc",
			limit_page_length=5,
		)
		if job_names
		else []
	)

	party = suppliers[0] if len(suppliers) == 1 else None
	log_portal_access("view_dashboard", party_type="Supplier", party=party)

	return {
		"active_jobs": active_count,
		"recent_jobs": recent_jobs,
	}
