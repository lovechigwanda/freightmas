# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, nowdate

from freightmas.forwarding_service.utils.service_order import (
	SERVICE_MODULE_SUPPLIER_FIELDS,
	append_charge_rows,
	build_scope_of_work,
	calculate_charge_amounts,
	get_eligible_cost_charge_rows,
	get_eligible_costing_charge_rows,
	get_enabled_service_modules,
	get_road_transport_creation_context,
	get_road_transport_milestones_for_service_order,
	get_service_instruction,
	get_road_transport_suppliers,
	is_service_module_enabled,
	link_cost_charges_to_service_order,
	link_parcels_to_service_order,
	populate_job_context,
	populate_road_transport_service_order,
	refresh_road_transport_service_order,
	resolve_default_supplier,
	unlink_cost_charges_from_service_order,
	unlink_parcels_from_service_order,
	validate_active_duplicate,
	validate_parcel_selection,
)
from freightmas.forwarding_service.utils.service_order_settings import get_default_service_order_terms
from freightmas.utils.permissions import check_doc_read_permission


class ServiceOrder(Document):
	def validate(self):
		self.ensure_service_instruction()
		self.validate_job_and_module()
		self.validate_charges()
		self.calculate_totals()
		self.update_status()

	def before_insert(self):
		if not self.prepared_by or self.prepared_by == "user":
			self.prepared_by = frappe.session.user
		if not self.terms_and_conditions:
			self.terms_and_conditions = get_default_service_order_terms()

	def before_save(self):
		if not self.forwarding_job_reference:
			return
		job = frappe.get_doc("Forwarding Job", self.forwarding_job_reference)
		populate_job_context(self, job)
		if self.service_module and self.supplier and not self.scope_of_work:
			self.scope_of_work = build_scope_of_work(job, self.service_module, self.supplier)
		self.ensure_service_instruction(job=job)

	def ensure_service_instruction(self, job=None):
		if self.service_instruction or not self.forwarding_job_reference:
			return
		if not self.service_module or not self.supplier:
			return
		if not job:
			job = frappe.get_doc("Forwarding Job", self.forwarding_job_reference)
		parcel_rows = None
		if self.service_module == "Road Transport" and len(self.get("service_order_parcels") or []):
			from freightmas.forwarding_service.utils.service_order import get_parcels_by_names
			parcel_refs = [row.cargo_parcel_reference for row in self.service_order_parcels]
			parcel_rows = get_parcels_by_names(job, parcel_refs, transporter=self.supplier)
		self.service_instruction = get_service_instruction(
			self.supplier, self.service_module, job, parcel_rows=parcel_rows
		)

	def on_submit(self):
		if not self.submitted_on:
			self.db_set("submitted_on", now(), update_modified=False)
		self.db_set("status", "Submitted", update_modified=False)
		if self.forwarding_job_reference:
			job = frappe.get_doc("Forwarding Job", self.forwarding_job_reference)
			link_cost_charges_to_service_order(job, self)
			if self.service_module == "Road Transport":
				link_parcels_to_service_order(job, self)

	def on_cancel(self):
		if self.purchase_invoice_reference:
			frappe.throw(_("Cannot cancel Service Order linked to Purchase Invoice {0}").format(
				self.purchase_invoice_reference
			))
		if self.forwarding_job_reference:
			job = frappe.get_doc("Forwarding Job", self.forwarding_job_reference)
			unlink_cost_charges_from_service_order(job, self.name)
			if self.service_module == "Road Transport":
				unlink_parcels_from_service_order(job, self.name)
		self.db_set("status", "Cancelled", update_modified=False)

	def validate_job_and_module(self):
		if not self.forwarding_job_reference or not self.service_module:
			return

		job = frappe.get_doc("Forwarding Job", self.forwarding_job_reference)
		if not is_service_module_enabled(job, self.service_module):
			frappe.throw(
				_("Service module {0} is not enabled on Forwarding Job {1}.")
				.format(self.service_module, job.name)
			)

		self.warn_supplier_agent_mismatch(job)

		if self.supplier and self.docstatus == 0:
			validate_active_duplicate(
				self.forwarding_job_reference,
				self.service_module,
				self.supplier,
				exclude_name=self.name if not self.is_new() else None,
			)

	def warn_supplier_agent_mismatch(self, job):
		agent_field = SERVICE_MODULE_SUPPLIER_FIELDS.get(self.service_module)
		if not agent_field or not self.supplier:
			return
		assigned_agent = job.get(agent_field)
		if assigned_agent and self.supplier != assigned_agent:
			frappe.msgprint(
				_("Warning: Supplier {0} differs from the job's assigned agent {1} for {2}.")
				.format(self.supplier, assigned_agent, self.service_module),
				indicator="orange",
				title=_("Supplier Mismatch"),
			)

	def validate_charges(self):
		if not self.get("service_order_charges"):
			frappe.throw(_("Add at least one charge line to the Service Order."))

		for row in self.service_order_charges:
			if not row.charge:
				frappe.throw(_("Each charge line must have a Charge item."))
			if not flt(row.buy_rate):
				frappe.throw(_("Each charge line must have a Buy Rate."))

	def calculate_totals(self):
		calculate_charge_amounts(self)

	def update_status(self):
		if self.docstatus == 2:
			status = "Cancelled"
		elif self.docstatus == 0:
			status = "Draft"
		elif self.purchase_invoice_reference:
			status = "Completed"
		else:
			status = "Submitted"
		if self.status != status:
			self.status = status

	@frappe.whitelist()
	def refresh_from_job(self):
		return refresh_service_order_scope(self.name)

	def get_road_transport_milestone_labels(self):
		return get_road_transport_milestones_for_service_order(self)


@frappe.whitelist()
def refresh_service_order_scope(docname):
	check_doc_read_permission("Service Order", docname)
	doc = frappe.get_doc("Service Order", docname)
	doc.check_permission("write")

	if not doc.forwarding_job_reference:
		frappe.throw(_("Link a Forwarding Job before refreshing scope."))
	if not doc.service_module or not doc.supplier:
		frappe.throw(_("Set Service Module and Supplier before refreshing scope."))

	job = frappe.get_doc("Forwarding Job", doc.forwarding_job_reference)
	populate_job_context(doc, job)

	if doc.service_module == "Road Transport":
		if len(doc.get("service_order_parcels") or []):
			refresh_road_transport_service_order(doc, job)
		else:
			doc.scope_of_work = build_scope_of_work(job, doc.service_module, doc.supplier)
			doc.service_instruction = get_service_instruction(
				doc.supplier, doc.service_module, job
			)
	else:
		doc.scope_of_work = build_scope_of_work(job, doc.service_module, doc.supplier)
		doc.service_instruction = get_service_instruction(
			doc.supplier, doc.service_module, job
		)

	doc.save()

	return {
		"scope_of_work": doc.scope_of_work,
		"service_instruction": doc.service_instruction,
		"tracking_milestones": doc.get("tracking_milestones"),
	}


@frappe.whitelist()
def get_service_order_creation_context(docname, service_module=None, supplier=None):
	check_doc_read_permission("Forwarding Job", docname)
	job = frappe.get_doc("Forwarding Job", docname)
	modules = get_enabled_service_modules(job)

	if service_module and service_module not in modules:
		frappe.throw(_("Service module {0} is not enabled on this job.").format(service_module))

	if not supplier and service_module:
		supplier = resolve_default_supplier(job, service_module)

	cost_rows = get_eligible_cost_charge_rows(job, supplier=supplier) if supplier else []
	costing_rows = get_eligible_costing_charge_rows(job, supplier=supplier) if supplier else []

	suppliers = get_road_transport_suppliers(job) if service_module == "Road Transport" else None
	road_transport_context = (
		get_road_transport_creation_context(job, transporter=supplier)
		if service_module == "Road Transport"
		else None
	)

	parcel_rows = None
	if service_module == "Road Transport" and supplier and road_transport_context:
		from freightmas.forwarding_service.utils.service_order import get_parcels_by_names
		parcel_names = [p["name"] for p in road_transport_context.get("parcels", []) if not p.get("already_ordered")]
		if parcel_names:
			parcel_rows = get_parcels_by_names(job, parcel_names, transporter=supplier)

	return {
		"service_modules": modules,
		"default_supplier": supplier,
		"road_transport_suppliers": suppliers,
		"road_transport_context": road_transport_context,
		"cost_charge_rows": [_serialize_charge_row(row) for row in cost_rows],
		"costing_charge_rows": [_serialize_charge_row(row) for row in costing_rows],
		"scope_of_work": build_scope_of_work(job, service_module, supplier, parcel_rows=parcel_rows)
		if service_module and (service_module != "Road Transport" or parcel_rows is not None)
		else "",
		"service_instruction": get_service_instruction(supplier, service_module, job, parcel_rows=parcel_rows)
		if service_module and supplier
		else "",
	}


@frappe.whitelist()
def get_road_transport_service_order_context(docname, transporter=None):
	check_doc_read_permission("Forwarding Job", docname)
	job = frappe.get_doc("Forwarding Job", docname)
	if not is_service_module_enabled(job, "Road Transport"):
		frappe.throw(_("Road Transport is not enabled on this job."))
	return get_road_transport_creation_context(job, transporter=transporter)


@frappe.whitelist()
def create_service_order_from_job(
	docname,
	service_module,
	supplier,
	row_names=None,
	parcel_names=None,
	required_by_date=None,
	special_instructions=None,
):
	check_doc_read_permission("Forwarding Job", docname)
	if row_names is not None and isinstance(row_names, str):
		row_names = frappe.parse_json(row_names) or []
	if parcel_names is not None and isinstance(parcel_names, str):
		parcel_names = frappe.parse_json(parcel_names) or []

	job = frappe.get_doc("Forwarding Job", docname)
	if not is_service_module_enabled(job, service_module):
		frappe.throw(_("Service module {0} is not enabled on this job.").format(service_module))
	if not supplier:
		frappe.throw(_("Supplier is required."))

	validate_active_duplicate(docname, service_module, supplier)

	service_order = frappe.new_doc("Service Order")
	service_order.forwarding_job_reference = docname
	service_order.service_module = service_module
	service_order.supplier = supplier
	service_order.order_date = nowdate()
	service_order.required_by_date = required_by_date
	service_order.special_instructions = special_instructions
	service_order.terms_and_conditions = get_default_service_order_terms()
	service_order.prepared_by = frappe.session.user
	populate_job_context(service_order, job)

	if service_module == "Road Transport":
		parcel_rows = validate_parcel_selection(job, supplier, parcel_names)
		populate_road_transport_service_order(service_order, job, supplier, parcel_rows)
	else:
		service_order.scope_of_work = build_scope_of_work(job, service_module, supplier)
		service_order.service_instruction = get_service_instruction(supplier, service_module, job)

		eligible_cost_rows = get_eligible_cost_charge_rows(job, supplier=supplier)
		eligible_costing_rows = get_eligible_costing_charge_rows(job, supplier=supplier)

		if row_names is not None:
			selected_cost_rows = [row for row in eligible_cost_rows if row.name in row_names]
			selected_costing_rows = [row for row in eligible_costing_rows if row.name in row_names]
		else:
			selected_cost_rows = eligible_cost_rows
			selected_costing_rows = []

		if selected_cost_rows:
			append_charge_rows(service_order, selected_cost_rows, from_costing=False)
		elif selected_costing_rows:
			append_charge_rows(service_order, selected_costing_rows, from_costing=True)
		elif row_names is not None and not row_names:
			frappe.throw(_("Please select at least one charge line."))
		elif not eligible_cost_rows and not eligible_costing_rows:
			frappe.throw(_("No charge lines found for supplier {0}.").format(supplier))

	calculate_charge_amounts(service_order)
	service_order.insert()
	return service_order.name


@frappe.whitelist()
def create_purchase_invoice_from_service_order(docname):
	check_doc_read_permission("Service Order", docname)
	service_order = frappe.get_doc("Service Order", docname)
	if service_order.docstatus != 1:
		frappe.throw(_("Service Order must be submitted before creating a Purchase Invoice."))
	if service_order.purchase_invoice_reference:
		frappe.throw(_("Purchase Invoice {0} already exists for this Service Order.").format(
			service_order.purchase_invoice_reference
		))

	charge_rows = [
		row for row in service_order.get("service_order_charges") or []
		if not row.is_invoiced
	]
	if not charge_rows:
		frappe.throw(_("No uninvoiced charge lines found on this Service Order."))

	job = frappe.get_doc("Forwarding Job", service_order.forwarding_job_reference)
	cost_row_names = [row.cost_charge_row for row in charge_rows if row.cost_charge_row]

	if cost_row_names:
		from freightmas.forwarding_service.doctype.forwarding_job.forwarding_job import (
			create_purchase_invoice_with_rows,
		)
		pi_name = create_purchase_invoice_with_rows(job.name, cost_row_names)
		if frappe.db.get_value("Purchase Invoice", pi_name, "service_order_reference") != service_order.name:
			frappe.db.set_value(
				"Purchase Invoice",
				pi_name,
				"service_order_reference",
				service_order.name,
				update_modified=False,
			)
	else:
		pi_name = _create_purchase_invoice_from_service_order_lines(service_order, job, charge_rows)

	service_order.db_set("purchase_invoice_reference", pi_name, update_modified=True)
	service_order.db_set("status", "Completed", update_modified=False)
	service_order.reload()

	for so_row in charge_rows:
		so_row.db_set("is_invoiced", 1, update_modified=False)
		so_row.db_set("purchase_invoice_reference", pi_name, update_modified=False)

	return pi_name


def _create_purchase_invoice_from_service_order_lines(service_order, job, charge_rows):
	"""Create PI directly from SO lines when no working cost charge rows exist."""
	from frappe.utils import nowdate

	pi = frappe.new_doc("Purchase Invoice")
	pi.supplier = service_order.supplier
	pi.company = service_order.company
	if service_order.currency:
		pi.currency = service_order.currency

	if pi.meta.get_field("forwarding_job_reference"):
		pi.forwarding_job_reference = job.name
	if pi.meta.get_field("is_forwarding_invoice"):
		pi.is_forwarding_invoice = 1
	if pi.meta.get_field("service_order_reference"):
		pi.service_order_reference = service_order.name

	pi.set_posting_time = 1
	pi.posting_date = nowdate()
	customer_ref = job.get("customer_reference") or "N/A"
	pi.remarks = f"{job.name}, Ref: {customer_ref}, SO: {service_order.name}"

	for row in charge_rows:
		pi.append("items", {
			"item_code": row.charge,
			"description": row.description or row.charge,
			"qty": row.qty or 1,
			"rate": row.buy_rate or 0,
		})

	pi.group_same_items = 0
	pi.insert()
	return pi.name


def _serialize_charge_row(row):
	return {
		"name": row.name,
		"charge": row.charge,
		"description": row.description or row.charge,
		"qty": row.qty or 1,
		"buy_rate": row.buy_rate or 0,
		"supplier": row.supplier,
	}
