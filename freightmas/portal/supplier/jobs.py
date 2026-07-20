# Supplier Portal read API: "My Jobs" list + detail across the job types a
# Supplier can be assigned to (Forwarding, Clearing, Border Clearing, Road
# Freight). Deliberately excludes the Customer's identity from every
# response - a supplier sees the operational shape of a job it is working
# on, never who the job is for.

import frappe
from frappe import _

from freightmas.portal.security import SUPPLIER_PORTAL_ROLE, check_portal_access, get_portal_supplier_names, log_portal_access
from freightmas.portal.supplier_scope import (
	CHARGE_TABLE_REGISTRY,
	assert_supplier_job_scope,
	get_supplier_job_names,
	get_supplier_scoped_charges,
)

# job_doctype -> operational (never customer-identifying) list fields.
JOB_TYPE_FIELDS = {
	"Forwarding Job": [
		"name", "status", "direction", "port_of_loading", "port_of_discharge",
		"vessel_flight_no", "bl_number", "eta", "ata", "etd", "atd",
		"cargo_count", "current_comment", "last_updated_on",
	],
	"Clearing Job": [
		"name", "status", "direction", "bl_number", "origin", "destination",
		"eta", "ata", "etd", "atd", "cargo_count", "cargo_description",
		"current_comment", "last_updated_on",
	],
	"Border Clearing Job": [
		"name", "status", "direction", "cargo_description", "current_comment", "last_updated_on",
	],
	"Road Freight Job": [
		"name", "status", "direction", "port_of_loading", "port_of_discharge", "cargo_description",
	],
}

DEFAULT_JOB_DOCTYPE = "Forwarding Job"


def _caller_supplier_filter():
	suppliers = get_portal_supplier_names()
	if not suppliers:
		frappe.throw(
			_("Your account is not linked to a supplier profile. Contact your account manager."),
			frappe.PermissionError,
		)
	return suppliers


def _assert_registered_job_doctype(job_doctype):
	if job_doctype not in CHARGE_TABLE_REGISTRY:
		frappe.throw(_("Unsupported job type."), frappe.ValidationError)


@frappe.whitelist()
def get_job_types():
	"""Job types the Supplier Portal supports, for the frontend's type filter."""
	check_portal_access(role=SUPPLIER_PORTAL_ROLE)
	return list(CHARGE_TABLE_REGISTRY.keys())


@frappe.whitelist()
def get_jobs(job_doctype=None, status=None, limit_start=0, limit_page_length=20):
	check_portal_access(role=SUPPLIER_PORTAL_ROLE)
	suppliers = _caller_supplier_filter()

	job_doctype = job_doctype or DEFAULT_JOB_DOCTYPE
	_assert_registered_job_doctype(job_doctype)

	party = suppliers[0] if len(suppliers) == 1 else None

	job_names = get_supplier_job_names(job_doctype, suppliers)
	if not job_names:
		log_portal_access("list_jobs", doctype=job_doctype, party_type="Supplier", party=party)
		return {"jobs": [], "total_count": 0}

	filters = {"name": ["in", job_names], "docstatus": ["<", 2]}
	if status:
		filters["status"] = status

	# get_all(), not get_list(): Supplier Portal User holds zero DocType
	# permissions by design (see freightmas/portal/security.py) - the
	# explicit name-list filter above is the actual access boundary.
	jobs = frappe.get_all(
		job_doctype,
		filters=filters,
		fields=JOB_TYPE_FIELDS[job_doctype],
		order_by="modified desc",
		limit_start=frappe.utils.cint(limit_start),
		limit_page_length=frappe.utils.cint(limit_page_length),
	)
	total_count = frappe.db.count(job_doctype, filters=filters)

	log_portal_access("list_jobs", doctype=job_doctype, party_type="Supplier", party=party)

	return {"jobs": jobs, "total_count": total_count}


@frappe.whitelist()
def get_job_detail(job_doctype, job_name):
	check_portal_access(role=SUPPLIER_PORTAL_ROLE)
	suppliers = _caller_supplier_filter()
	_assert_registered_job_doctype(job_doctype)

	assert_supplier_job_scope(job_doctype, job_name, suppliers)

	header = frappe.db.get_value(job_doctype, job_name, JOB_TYPE_FIELDS[job_doctype], as_dict=True)
	charges = get_supplier_scoped_charges(job_doctype, job_name, suppliers)

	party = suppliers[0] if len(suppliers) == 1 else None
	log_portal_access("view_job", doctype=job_doctype, docname=job_name, party_type="Supplier", party=party)

	return {
		"header": header,
		"charges": charges,
	}
