# Supplier Portal child-row scoping.
#
# Unlike a Customer, which owns a job via a single parent-level field, a
# Supplier's relationship to a job lives at TWO different levels that must
# both be handled:
#
#   1. An explicit named role on the job itself (origin agent, port
#      clearing agent, border clearing agent) - a real, indexed,
#      parent-level Link field.
#   2. Per-line cost/charge child tables, where a single job can carry
#      rows from several different suppliers at once, mixed in with
#      customer-facing fields (sell_rate, revenue_amount, margin) on the
#      SAME row.
#
# This module is kept separate from security.py because its logic is more
# doctype-specific and higher-risk than the generic party-resolution
# primitives there - isolating it means a mistake here can't silently
# regress the simpler, already-tested Customer scope path.
#
# Field lists below are POSITIVE allowlists, not blocklists: only fields
# named here are ever returned. A blocklist would silently leak any new
# sensitive field added to a child doctype in the future; an allowlist
# silently omits it until an implementer notices it's missing, which is
# the safe failure direction.

import frappe

# job_doctype -> parent-level Link-to-Supplier field(s) that name an agent
# role on that job. Road Freight Job has no such parent-level field - its
# transporter role only exists per-truck, in Truck Loading Details - so it
# is deliberately absent here and handled via CHARGE_TABLE_REGISTRY instead.
ROLE_FIELD_REGISTRY = {
	"Forwarding Job": ["origin_agent"],
	"Clearing Job": ["port_clearing_agent"],
	"Border Clearing Job": ["clearing_agent"],
}

# job_doctype -> list of {fieldname, child_doctype, supplier_field}
# describing every child table on that job which can carry supplier-owned
# rows, and which fieldname on the child table holds the Supplier link.
CHARGE_TABLE_REGISTRY = {
	"Forwarding Job": [
		{"fieldname": "forwarding_costing_charges", "child_doctype": "Forwarding Costing Charges", "supplier_field": "supplier"},
		{"fieldname": "forwarding_cost_charges", "child_doctype": "Forwarding Cost Charges", "supplier_field": "supplier"},
	],
	"Clearing Job": [
		{"fieldname": "clearing_costing_charges", "child_doctype": "Clearing Costing Charges", "supplier_field": "supplier"},
		{"fieldname": "clearing_cost_charges", "child_doctype": "Clearing Cost Charges", "supplier_field": "supplier"},
	],
	"Border Clearing Job": [
		{"fieldname": "border_clearing_costing_charges", "child_doctype": "Border Clearing Costing Charges", "supplier_field": "supplier"},
		{"fieldname": "border_clearing_cost_charges", "child_doctype": "Border Clearing Cost Charges", "supplier_field": "supplier"},
	],
	"Road Freight Job": [
		{"fieldname": "road_freight_charges", "child_doctype": "Road Freight Charges", "supplier_field": "supplier"},
		{"fieldname": "truck_loading_details", "child_doctype": "Truck Loading Details", "supplier_field": "transporter"},
	],
}

# child_doctype -> allowlisted fields. Never includes customer, sell_rate,
# revenue_amount, margin_amount, margin_percentage, sales_invoice_reference,
# selling_rate, or is_invoiced - those exist on several of these tables
# (mixed in with the supplier-safe fields on the very same row) and must
# never reach a supplier-facing endpoint.
SAFE_CHARGE_FIELDS = {
	"Forwarding Costing Charges": ["name", "charge", "description", "qty", "buy_rate", "cost_amount", "supplier"],
	"Forwarding Cost Charges": [
		"name", "charge", "description", "qty", "buy_rate", "cost_amount", "supplier",
		"is_purchased", "purchase_invoice_reference", "supplier_invoice_no", "supplier_invoice_date",
	],
	"Clearing Costing Charges": ["name", "charge", "description", "qty", "buy_rate", "cost_amount", "supplier"],
	"Clearing Cost Charges": [
		"name", "charge", "description", "qty", "buy_rate", "cost_amount", "supplier",
		"is_purchased", "purchase_invoice_reference", "supplier_invoice_no", "supplier_invoice_date",
	],
	"Border Clearing Costing Charges": ["name", "charge", "description", "qty", "buy_rate", "cost_amount", "supplier", "is_pass_through"],
	"Border Clearing Cost Charges": [
		"name", "charge", "description", "qty", "buy_rate", "cost_amount", "supplier", "is_pass_through",
		"is_purchased", "purchase_invoice_reference", "supplier_invoice_no", "supplier_invoice_date",
	],
	"Road Freight Charges": [
		"name", "charge", "description", "qty", "buy_rate", "cost_amount", "supplier",
		"is_purchased", "purchase_invoice_reference",
	],
	"Truck Loading Details": ["name", "transporter", "container_type", "cargo_uom", "service_charge", "buying_rate"],
}


def get_supplier_job_names(job_doctype, supplier_names):
	"""Return names of jobs of job_doctype where any of supplier_names holds
	the job's named agent role (or, for Road Freight Job, is a transporter
	on at least one Truck Loading Details row).

	Deliberately does NOT include jobs where a supplier only appears on a
	cost/costing charge line without holding a named role - that is a
	distinct, broader question answered by get_supplier_scoped_charges,
	not by this function.
	"""
	if not supplier_names:
		return []

	if job_doctype in ROLE_FIELD_REGISTRY:
		role_fields = ROLE_FIELD_REGISTRY[job_doctype]
		if len(role_fields) == 1:
			filters = {role_fields[0]: ["in", supplier_names], "docstatus": ["<", 2]}
			return frappe.get_all(job_doctype, filters=filters, pluck="name")

		or_filters = [[job_doctype, field, "in", supplier_names] for field in role_fields]
		return frappe.get_all(
			job_doctype, filters={"docstatus": ["<", 2]}, or_filters=or_filters, pluck="name"
		)

	if job_doctype == "Road Freight Job":
		return list(
			dict.fromkeys(
				frappe.get_all(
					"Truck Loading Details",
					filters={"parenttype": "Road Freight Job", "transporter": ["in", supplier_names]},
					pluck="parent",
				)
			)
		)

	frappe.throw(f"{job_doctype} is not a registered supplier-portal job type")


def get_supplier_scoped_charges(job_doctype, job_name, supplier_names):
	"""Return this supplier's own charge-line rows on one job, grouped by
	child table fieldname, with only the safe-field allowlist applied.

	Never returns another supplier's rows on the same job, and never
	includes a cross-row aggregate (e.g. a job total) that could indirectly
	reveal margin by comparison against a customer-visible total shown
	elsewhere - a future "show me my total on this job" feature must sum
	only the rows this function already returns, not compute anything new.
	"""
	if job_doctype not in CHARGE_TABLE_REGISTRY:
		frappe.throw(f"{job_doctype} is not a registered supplier-portal job type")

	if not supplier_names:
		return {}

	result = {}
	for entry in CHARGE_TABLE_REGISTRY[job_doctype]:
		fields = SAFE_CHARGE_FIELDS[entry["child_doctype"]]
		rows = frappe.get_all(
			entry["child_doctype"],
			filters={
				"parenttype": job_doctype,
				"parent": job_name,
				entry["supplier_field"]: ["in", supplier_names],
			},
			fields=fields,
			order_by="idx asc",
		)
		result[entry["fieldname"]] = rows
	return result


def assert_supplier_job_scope(job_doctype, job_name, supplier_names):
	"""Verify the caller's supplier(s) are entitled to see this job - either
	by holding a named role on it, or by having at least one charge-line
	row on it.

	Raises:
		frappe.PermissionError: if neither condition holds.
	"""
	if not supplier_names:
		frappe.throw("You do not have permission to view this record.", frappe.PermissionError)

	if job_name in get_supplier_job_names(job_doctype, supplier_names):
		return

	charges = get_supplier_scoped_charges(job_doctype, job_name, supplier_names)
	if any(rows for rows in charges.values()):
		return

	frappe.throw("You do not have permission to view this record.", frappe.PermissionError)
