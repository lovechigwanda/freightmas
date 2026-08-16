# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from freightmas.forwarding_service.utils.service_order_settings import get_default_service_order_terms

SERVICE_MODULE_OPTIONS = [
	"Sea/Air Freight",
	"Road Freight",
	"Port Clearance",
	"Road Transport",
	"Border Clearance",
	"Warehouse",
]

SERVICE_MODULE_JOB_FLAGS = {
	"Sea/Air Freight": "requires_sea_air_freight",
	"Port Clearance": "requires_port_clearance",
	"Road Transport": "is_trucking_required",
	"Border Clearance": "requires_border_clearance",
	"Warehouse": "requires_warehousing",
}

SERVICE_MODULE_SUPPLIER_FIELDS = {
	"Sea/Air Freight": "origin_agent",
	"Port Clearance": "port_clearing_agent",
	"Border Clearance": "border_clearing_agent",
}

SERVICE_MODULE_MILESTONE_TABLES = {
	"Port Clearance": "port_clearance_milestones",
	"Border Clearance": "border_clearance_milestones",
	"Warehouse": "warehouse_milestones",
	"Road Freight": "road_freight_milestones",
}


def get_enabled_service_modules(job):
	"""Return service modules enabled on a Forwarding Job."""
	modules = []
	for module, flag in SERVICE_MODULE_JOB_FLAGS.items():
		if job.get(flag):
			modules.append(module)

	if job.get("shipment_mode") == "Road" and "Road Freight" not in modules:
		modules.append("Road Freight")

	return modules


def is_service_module_enabled(job, service_module):
	if service_module == "Road Freight":
		return job.get("shipment_mode") == "Road"
	flag = SERVICE_MODULE_JOB_FLAGS.get(service_module)
	return bool(flag and job.get(flag))


def resolve_default_supplier(job, service_module):
	if service_module == "Road Transport":
		transporters = {
			row.transporter
			for row in job.get("cargo_parcel_details") or []
			if row.get("is_truck_required") and row.get("transporter")
		}
		return sorted(transporters)[0] if len(transporters) == 1 else None

	fieldname = SERVICE_MODULE_SUPPLIER_FIELDS.get(service_module)
	if fieldname:
		return job.get(fieldname)

	suppliers = get_suppliers_from_charges(job)
	return suppliers[0] if len(suppliers) == 1 else None


def get_suppliers_from_charges(job):
	suppliers = set()
	for table in ("forwarding_cost_charges", "forwarding_costing_charges"):
		for row in job.get(table) or []:
			if row.get("supplier"):
				suppliers.add(row.supplier)
	return sorted(suppliers)


def get_road_transport_suppliers(job):
	return sorted({
		row.transporter
		for row in job.get("cargo_parcel_details") or []
		if row.get("is_truck_required") and row.get("transporter")
	})


def get_eligible_cost_charge_rows(job, supplier=None, exclude_ordered=True):
	rows = []
	for row in job.get("forwarding_cost_charges") or []:
		if exclude_ordered and row.get("is_ordered"):
			continue
		if exclude_ordered and row.get("is_purchased"):
			continue
		if supplier and row.get("supplier") != supplier:
			continue
		if not row.get("charge") or not row.get("buy_rate") or not row.get("supplier"):
			continue
		rows.append(row)
	return rows


def get_eligible_costing_charge_rows(job, supplier=None):
	"""Costing rows used when working cost rows are not yet populated."""
	existing_keys = {
		(row.charge, flt(row.buy_rate), row.supplier)
		for row in job.get("forwarding_cost_charges") or []
	}
	rows = []
	for row in job.get("forwarding_costing_charges") or []:
		if supplier and row.get("supplier") != supplier:
			continue
		if not row.get("charge") or not row.get("buy_rate") or not row.get("supplier"):
			continue
		key = (row.charge, flt(row.buy_rate), row.supplier)
		if key in existing_keys:
			continue
		rows.append(row)
	return rows


def build_scope_of_work(job, service_module, supplier=None, parcel_rows=None):
	context = get_scope_print_context(job, service_module, supplier, parcel_rows=parcel_rows)
	return _render_scope_html(context)


def get_scope_print_context(job, service_module, supplier=None, parcel_rows=None):
	if service_module == "Road Transport" and parcel_rows is not None:
		return _get_road_transport_scope_context(job, supplier, parcel_rows)

	rows = _collect_scope_rows(job, service_module, supplier)
	split_at = (len(rows) + 1) // 2
	return {
		"left_rows": rows[:split_at],
		"right_rows": rows[split_at:],
		"milestones": _collect_milestone_labels(job, service_module),
	}


def get_scope_print_layout(job, service_module, supplier=None):
	rows = _collect_scope_rows(job, service_module, supplier)
	row_dict = {label: value for label, value in rows}

	def val(label, default="—"):
		value = row_dict.get(label)
		return value if value not in (None, "") else default

	grid_columns, full_width_rows = _scope_print_grid(job, service_module, supplier, val)
	return {
		"grid_columns": grid_columns,
		"full_width_rows": full_width_rows,
		"milestones": _collect_milestone_labels(job, service_module),
		"service_instruction": get_service_instruction(supplier, service_module, job),
	}


def get_service_instruction(supplier, service_module, job, parcel_rows=None):
	supplier_name = supplier or _("the Supplier")
	pod = job.get("port_of_discharge") or _("port of discharge")
	pol = job.get("port_of_loading") or _("port of loading")
	destination = job.get("destination") or _("destination")
	route = job.get("route") or job.get("road_freight_route") or destination
	closing = _("Please proceed in accordance with the scope of work and charges stated below.")

	if service_module == "Port Clearance":
		return _(
			"We hereby nominate {0} as our port clearance agent at {1} for the shipment detailed above. {2}"
		).format(supplier_name, pod, closing)

	if service_module == "Sea/Air Freight":
		return _(
			"We hereby instruct {0} to arrange carriage of the shipment detailed above from {1} to {2}. "
			"The agreed scope of work and charges are set out below."
		).format(supplier_name, pol, pod or destination)

	if service_module == "Border Clearance":
		return _(
			"We hereby appoint {0} as our border clearing agent for the shipment detailed above "
			"to {1}. {2}"
		).format(supplier_name, destination, closing)

	if service_module == "Road Transport":
		return get_road_transport_service_instruction(supplier_name, job, parcel_rows or [])

	if service_module == "Road Freight":
		return _(
			"We hereby instruct {0} to provide road freight services for the shipment detailed above "
			"on route {1}. The agreed scope of work and charges are set out below."
		).format(supplier_name, route)

	if service_module == "Warehouse":
		return _(
			"We hereby instruct {0} to provide warehousing services for the cargo detailed above. "
			"The agreed scope of work and charges are set out below."
		).format(supplier_name)

	return _(
		"We hereby instruct {0} to provide {1} services for the shipment detailed above. "
		"The agreed scope of work and charges are set out below."
	).format(supplier_name, service_module)


def get_nomination_statement(supplier, service_module, job):
	"""Backward-compatible alias."""
	return get_service_instruction(supplier, service_module, job)


def _scope_print_grid(job, service_module, supplier, val):
	if service_module == "Port Clearance":
		return [
			[("Reference No.", val("Reference No.")), ("Direction", val("Direction"))],
			[("BL Number", val("BL Number")), ("Port of Discharge", val("Port of Discharge"))],
			[("Shipping Line", val("Shipping Line")), ("Destination", val("Destination"))],
		], [("Container/Cargo Count", val("Container/Cargo Count"))]

	if service_module == "Sea/Air Freight":
		return [
			[("Reference No.", val("Reference No.")), ("Direction", val("Direction"))],
			[("BL Number", val("BL Number")), ("Port of Discharge", val("Port of Discharge"))],
			[("Shipping Line", val("Shipping Line")), ("Destination", val("Destination"))],
		], [
			("Vessel/Flight", val("Vessel/Flight")),
			("ETD / ETA", f"{val('ETD')} / {val('ETA')}"),
			("Container/Cargo Count", val("Container/Cargo Count")),
		]

	if service_module == "Border Clearance":
		return [
			[("Reference No.", val("Reference No.")), ("Direction", val("Direction"))],
			[("Cargo", val("Cargo")), ("Destination", val("Destination"))],
			[("Border Clearing Agent", val("Border Clearing Agent")), ("Incoterms", val("Incoterms"))],
		], []

	if service_module == "Road Transport":
		return [
			[("Reference No.", val("Reference No.")), ("Direction", val("Direction"))],
			[("Cargo", val("Cargo")), ("Destination", val("Destination"))],
			[("Route", val("Route")), ("Loading Address", val("Loading Address"))],
		], [("Offloading Address", val("Offloading Address"))]

	if service_module == "Road Freight":
		return [
			[("Reference No.", val("Reference No.")), ("Direction", val("Direction"))],
			[("Road Route", val("Road Route")), ("Destination", val("Destination"))],
			[("Trucks Required", val("Trucks Required")), ("Incoterms", val("Incoterms"))],
		], []

	return _generic_scope_print_grid(job, service_module, supplier, val)


def _generic_scope_print_grid(job, service_module, supplier, val):
	rows = _collect_scope_rows(job, service_module, supplier)
	if not rows:
		return [], []

	pairs = list(rows)
	grid = []
	for col_idx in range(3):
		column = []
		for row_idx in range(col_idx, len(pairs), 3):
			column.append(pairs[row_idx])
		if column:
			grid.append(column[:2] if len(column) > 2 else column)

	while len(grid) < 3:
		grid.append([])

	full_width = []
	if len(pairs) > 6:
		full_width = pairs[6:]

	return grid[:3], full_width


def _collect_milestone_labels(job, service_module):
	table_map = {
		"Port Clearance": "port_clearance_milestones",
		"Border Clearance": "border_clearance_milestones",
		"Warehouse": "warehouse_milestones",
		"Road Freight": "road_freight_milestones",
	}
	table_field = table_map.get(service_module)
	if not table_field:
		return []
	return [
		row.milestone_label or row.milestone or row.milestone_code
		for row in (job.get(table_field) or [])
	]


def _scope_row(label, value):
	if value is None or value == "":
		return None
	return (label, value)


def _collect_scope_rows(job, service_module, supplier=None):
	rows = [
		_scope_row("Reference No.", job.name),
		_scope_row("Cargo", job.get("cargo_description")),
		_scope_row("Direction", job.get("direction")),
		_scope_row("Shipment Mode", job.get("shipment_mode")),
		_scope_row("Incoterms", job.get("incoterms")),
		_scope_row("Port of Loading", job.get("port_of_loading")),
		_scope_row("Port of Discharge", job.get("port_of_discharge")),
		_scope_row("Destination", job.get("destination")),
	]

	rows.extend(_module_scope_rows(job, service_module, supplier))
	return [row for row in rows if row]


def _module_scope_rows(job, service_module, supplier=None):
	rows = []

	if service_module == "Sea/Air Freight":
		rows.extend([
			_scope_row("BL Number", job.get("bl_number")),
			_scope_row("Shipping Line", job.get("shipping_line")),
			_scope_row("Vessel/Flight", job.get("vessel_flight_no")),
			_scope_row("ETD", getdate(job.etd) if job.get("etd") else None),
			_scope_row("ETA", getdate(job.eta) if job.get("eta") else None),
		])

	elif service_module == "Port Clearance":
		rows.extend([
			_scope_row("BL Number", job.get("bl_number")),
			_scope_row("Shipping Line", job.get("shipping_line")),
			_scope_row("Container/Cargo Count", job.get("cargo_count")),
		])

	elif service_module == "Border Clearance":
		rows.extend([
			_scope_row("Border Clearing Agent", job.get("border_clearing_agent")),
		])

	elif service_module == "Road Transport":
		if job.get("loading_address"):
			rows.append(_scope_row("Loading Address", job.get("loading_address")))
		if job.get("offloadiing_address"):
			rows.append(_scope_row("Offloading Address", job.get("offloadiing_address")))
		if job.get("route"):
			rows.append(_scope_row("Route", job.get("route")))
		if job.get("loading_instructions"):
			rows.append(_scope_row("Loading Instructions", job.get("loading_instructions")))
		rows.extend(_road_transport_parcel_rows(job, supplier))

	elif service_module == "Warehouse":
		pass

	elif service_module == "Road Freight":
		rows.extend([
			_scope_row("Road Route", job.get("road_freight_route")),
			_scope_row("Trucks Required", job.get("trucks_required")),
		])

	return [row for row in rows if row]


def _road_transport_parcel_rows(job, supplier=None):
	parcels = [
		row for row in job.get("cargo_parcel_details") or []
		if row.get("is_truck_required") and (not supplier or row.get("transporter") == supplier)
	]
	rows = []
	for idx, row in enumerate(parcels, start=1):
		label = row.get("truck_reg_no") or f"Parcel {idx}"
		value = f"Qty {row.get('cargo_quantity') or 1}, Rate {row.get('truck_buying_rate') or 0}"
		rows.append((label, value))
	return rows


# --- Road Transport (parcel-driven) ---


def get_parcel_cargo_label(parcel):
	return (
		parcel.get("container_number")
		or parcel.get("cargo_item_description")
		or parcel.get("name")
	)


def get_parcel_display_title(parcel):
	cargo_type = (parcel.get("cargo_type") or "").strip()
	if cargo_type == "Containerised":
		parts = []
		if parcel.get("container_number"):
			parts.append(parcel.get("container_number"))
		if parcel.get("container_type"):
			qty = cint(parcel.get("cargo_quantity")) or 1
			parts.append(f"{qty}X {parcel.get('container_type')}")
		if parts:
			return " ".join(parts)

	if parcel.get("cargo_item_description"):
		return parcel.get("cargo_item_description")

	return get_parcel_cargo_label(parcel)


def get_ordered_parcel_references(forwarding_job, exclude_service_order=None):
	rows = frappe.db.sql(
		"""
		SELECT cpd.name
		FROM `tabCargo Parcel Details` cpd
		INNER JOIN `tabService Order` so ON so.name = cpd.service_order_reference
		WHERE cpd.parent = %s
			AND cpd.service_order_reference IS NOT NULL
			AND cpd.service_order_reference != ''
			AND so.docstatus = 1
		""",
		forwarding_job,
		as_list=True,
	)
	ordered = {row[0] for row in rows}
	if exclude_service_order:
		ordered -= set(
			frappe.get_all(
				"Service Order Parcels",
				filters={"parent": exclude_service_order},
				pluck="cargo_parcel_reference",
			)
		)
	return ordered


def get_parcels_on_open_service_orders(forwarding_job, parcel_names, exclude_service_order=None):
	if not parcel_names:
		return {}

	filters = {
		"parenttype": "Service Order",
		"cargo_parcel_reference": ["in", parcel_names],
	}
	rows = frappe.get_all(
		"Service Order Parcels",
		filters=filters,
		fields=["cargo_parcel_reference", "parent"],
	)
	result = {}
	for row in rows:
		so_name = row.parent
		if exclude_service_order and so_name == exclude_service_order:
			continue
		job_ref, docstatus = frappe.db.get_value("Service Order", so_name, [
			"forwarding_job_reference", "docstatus"
		]) or (None, None)
		if job_ref != forwarding_job or docstatus == 2:
			continue
		result[row.cargo_parcel_reference] = so_name
	return result


def get_road_transport_parcels(job, transporter=None):
	parcels = [
		row for row in job.get("cargo_parcel_details") or []
		if row.get("is_truck_required") and row.get("transporter")
		and (not transporter or row.get("transporter") == transporter)
	]
	return parcels


def serialize_parcel_for_dialog(parcel, ordered_refs=None):
	ordered_refs = ordered_refs or set()
	errors = []
	if not parcel.get("service_charge"):
		errors.append(_("Service Charge is required"))
	if not flt(parcel.get("truck_buying_rate")):
		errors.append(_("Transporter Rate is required"))

	return {
		"name": parcel.name,
		"cargo_label": get_parcel_display_title(parcel),
		"cargo_type": parcel.get("cargo_type"),
		"container_number": parcel.get("container_number"),
		"container_type": parcel.get("container_type"),
		"cargo_item_description": parcel.get("cargo_item_description"),
		"loading_address": parcel.get("cargo_loading_address"),
		"offloading_address": parcel.get("cargo_offloading_address"),
		"drop_off_place": parcel.get("drop_off_place"),
		"load_by_date": parcel.get("load_by_date"),
		"to_be_returned": parcel.get("to_be_returned"),
		"return_by_date": parcel.get("return_by_date"),
		"truck_reg_no": parcel.get("truck_reg_no"),
		"trailer_reg_no": parcel.get("trailer_reg_no"),
		"driver_name": parcel.get("driver_name"),
		"service_charge": parcel.get("service_charge"),
		"transporter_rate": flt(parcel.get("truck_buying_rate")),
		"already_ordered": parcel.name in ordered_refs,
		"validation_errors": errors,
	}


def get_road_transport_creation_context(job, transporter=None):
	transporters = get_road_transport_suppliers(job)
	ordered_refs = get_ordered_parcel_references(job.name)
	parcels = [
		serialize_parcel_for_dialog(row, ordered_refs)
		for row in get_road_transport_parcels(job, transporter=transporter)
	]
	return {
		"transporters": transporters,
		"default_transporter": transporters[0] if len(transporters) == 1 else None,
		"parcels": parcels,
	}


def get_parcels_by_names(job, parcel_names, transporter=None):
	parcel_map = {row.name: row for row in get_road_transport_parcels(job, transporter=transporter)}
	selected = []
	for name in parcel_names or []:
		if name not in parcel_map:
			frappe.throw(_("Cargo parcel {0} was not found for the selected transporter.").format(name))
		selected.append(parcel_map[name])
	return selected


def validate_parcel_selection(job, transporter, parcel_names):
	if not parcel_names:
		frappe.throw(_("Select at least one cargo parcel."))

	selected = get_parcels_by_names(job, parcel_names, transporter=transporter)
	ordered_refs = get_ordered_parcel_references(job.name)
	open_refs = get_parcels_on_open_service_orders(job.name, parcel_names)

	for parcel in selected:
		if parcel.name in ordered_refs:
			frappe.throw(
				_("Cargo parcel {0} is already linked to a submitted Service Order.")
				.format(get_parcel_cargo_label(parcel))
			)
		if parcel.name in open_refs:
			frappe.throw(
				_("Cargo parcel {0} is already included on Service Order {1}.")
				.format(get_parcel_cargo_label(parcel), open_refs[parcel.name])
			)
		errors = serialize_parcel_for_dialog(parcel)["validation_errors"]
		if errors:
			frappe.throw(
				_("Cargo parcel {0}: {1}").format(get_parcel_cargo_label(parcel), ", ".join(errors))
			)

	return selected


def build_service_order_parcel_row(parcel):
	return {
		"cargo_parcel_reference": parcel.name,
		"cargo_label": get_parcel_display_title(parcel),
		"cargo_type": parcel.get("cargo_type"),
		"container_number": parcel.get("container_number"),
		"container_type": parcel.get("container_type"),
		"cargo_item_description": parcel.get("cargo_item_description"),
		"loading_address": parcel.get("cargo_loading_address"),
		"offloading_address": parcel.get("cargo_offloading_address"),
		"drop_off_place": parcel.get("drop_off_place"),
		"load_by_date": parcel.get("load_by_date"),
		"to_be_returned": parcel.get("to_be_returned"),
		"return_by_date": parcel.get("return_by_date"),
		"road_freight_route": parcel.get("road_freight_route"),
		"truck_reg_no": parcel.get("truck_reg_no"),
		"trailer_reg_no": parcel.get("trailer_reg_no"),
		"driver_name": parcel.get("driver_name"),
		"service_charge": parcel.get("service_charge"),
		"transporter_rate": flt(parcel.get("truck_buying_rate")),
		"border_tracking": parcel.get("border_tracking"),
		"border_2_tracking": parcel.get("border_2_tracking"),
		"offloading_point": parcel.get("offloading_point"),
	}


def append_parcel_charge_rows(service_order, parcel_rows):
	for parcel in parcel_rows:
		label = get_parcel_cargo_label(parcel)
		service_order.append("service_order_charges", {
			"charge": parcel.service_charge,
			"description": _("Road Transport - {0}").format(label),
			"qty": 1,
			"buy_rate": flt(parcel.truck_buying_rate),
			"cargo_parcel_reference": parcel.name,
		})


def ensure_cost_charge_rows_for_parcels(job, parcel_rows):
	existing_by_ref = {
		row.source_reference: row
		for row in job.get("forwarding_cost_charges") or []
		if row.get("source_reference")
	}
	changed = False

	for parcel in parcel_rows:
		if parcel.name in existing_by_ref:
			continue

		job.append("forwarding_cost_charges", {
			"charge": parcel.service_charge,
			"description": _("Truck Loading Service - {0}").format(get_parcel_cargo_label(parcel)),
			"qty": 1,
			"buy_rate": flt(parcel.truck_buying_rate),
			"supplier": parcel.transporter,
			"cost_amount": flt(parcel.truck_buying_rate),
			"source_reference": parcel.name,
		})
		changed = True

	if changed:
		job.save(ignore_permissions=True)


def link_cost_charge_rows_for_parcels(service_order, job):
	cost_by_ref = {
		row.source_reference: row.name
		for row in job.get("forwarding_cost_charges") or []
		if row.get("source_reference")
	}
	for so_row in service_order.get("service_order_charges") or []:
		ref = so_row.get("cargo_parcel_reference")
		if ref and ref in cost_by_ref:
			so_row.cost_charge_row = cost_by_ref[ref]


def get_road_transport_milestones(parcel_rows):
	labels = [_("Is Loaded")]

	if any(row.get("border_tracking") for row in parcel_rows):
		labels.extend([_("Border Arrived"), _("Border Departed")])

	if any(row.get("border_2_tracking") for row in parcel_rows):
		labels.extend([_("Border 2 Arrived"), _("Border 2 Departed")])

	if any(row.get("offloading_point") for row in parcel_rows):
		labels.append(_("Offloading Point Arrived"))

	labels.append(_("Is Offloaded"))

	if any(row.get("to_be_returned") for row in parcel_rows):
		labels.append(_("Is Returned"))

	labels.append(_("Is Completed"))
	return labels


def get_road_transport_milestones_for_service_order(service_order):
	parcel_rows = [
		frappe._dict({
			"border_tracking": row.border_tracking,
			"border_2_tracking": row.border_2_tracking,
			"offloading_point": row.offloading_point,
			"to_be_returned": row.to_be_returned,
		})
		for row in (service_order.get("service_order_parcels") or [])
	]
	return get_road_transport_milestones(parcel_rows)


def render_tracking_milestones_html(labels):
	if not labels:
		return ""
	return _render_milestone_table_html(labels, include_heading=True)


def _render_milestone_table_html(labels, include_heading=False):
	count = len(labels)
	per_col = (count + 2) // 3
	columns = []
	for col in range(3):
		items = []
		for i in range(col * per_col, (col + 1) * per_col):
			if i < count:
				items.append(f"{i + 1}. {labels[i]}")
		columns.append("<br>".join(items))

	heading = ""
	if include_heading:
		heading = (
			f"<strong>{_('Tracking Milestones')}</strong><br>"
			f"{_('Please provide tracking updates as each milestone below is reached.')}<br>"
		)

	return (
		f"<div style='margin-top:4px;font-size:13px;line-height:1.35;'>"
		f"{heading}"
		f"<table class='milestone-table' style='width:100%;border-collapse:collapse;'>"
		f"<tr>"
		f"{''.join(f'<td style=\"width:33.33%;vertical-align:top;padding:0 8px 0 0;font-size:12px;line-height:1.35;\">{column}</td>' for column in columns)}"
		f"</tr></table></div>"
	)


def get_road_transport_service_instruction(supplier_name, job, parcel_rows):
	return _(
		"We hereby instruct {0} to transport the cargo detailed below. "
		"Please provide tracking updates as each milestone below is reached."
	).format(supplier_name)


def _get_road_transport_scope_context(job, supplier, parcel_rows):
	return {
		"road_transport": True,
		"reference_no": job.name,
		"direction": job.get("direction"),
		"destination": job.get("destination"),
		"parcels": parcel_rows,
		"milestones": get_road_transport_milestones(parcel_rows),
	}


def _render_road_transport_scope_html(context):
	parts = [
		f"<table style='width:100%;border-collapse:collapse;'>"
		f"<tr><td style='padding:2px 0;line-height:1.1;font-size:13px;'>"
		f"Reference No.: {context.get('reference_no') or '—'}<br>"
		f"Direction: {context.get('direction') or '—'}<br>"
		f"Destination: {context.get('destination') or '—'}"
		f"</td></tr></table>"
	]

	for idx, parcel in enumerate(context.get("parcels") or [], start=1):
		return_text = _("Yes") if parcel.get("to_be_returned") else _("No")
		if parcel.get("to_be_returned") and parcel.get("return_by_date"):
			return_text = f"{return_text} ({frappe.format_value(parcel.get('return_by_date'), {'fieldtype': 'Date'})})"

		parts.append(
			f"<div style='margin-top:6px;padding-top:4px;border-top:1px solid #ddd;font-size:13px;line-height:1.2;'>"
			f"<strong>{_('Parcel')} {idx}: {get_parcel_display_title(parcel)}</strong><br>"
			f"{_('Loading Address')}: {parcel.get('loading_address') or parcel.get('cargo_loading_address') or '—'}<br>"
			f"{_('Offloading Address')}: {parcel.get('offloading_address') or parcel.get('cargo_offloading_address') or '—'}<br>"
			f"{_('Drop Off Place')}: {parcel.get('drop_off_place') or '—'}<br>"
			f"{_('Load By Date')}: {frappe.format_value(parcel.get('load_by_date'), {'fieldtype': 'Date'}) or '—'} | "
			f"{_('Return Required')}: {return_text}<br>"
			f"{_('Truck Reg')}: {parcel.get('truck_reg_no') or '—'} | "
			f"{_('Trailer Reg')}: {parcel.get('trailer_reg_no') or '—'} | "
			f"{_('Driver')}: {parcel.get('driver_name') or '—'}<br>"
			f"{_('Service Charge')}: {parcel.get('service_charge') or '—'} | "
			f"{_('Transporter Rate')}: {flt(parcel.get('transporter_rate') or parcel.get('truck_buying_rate'))}"
			f"</div>"
		)

	return "".join(parts)


def _render_scope_html(context):
	if context.get("road_transport"):
		return _render_road_transport_scope_html(context)

	left_rows = context["left_rows"]
	right_rows = context["right_rows"]
	milestone_html = _format_milestone_html(context["milestones"])
	return _render_two_column_scope(left_rows, right_rows, milestone_html)


def populate_road_transport_service_order(service_order, job, transporter, parcel_rows):
	service_order.service_order_parcels = []
	for parcel in parcel_rows:
		service_order.append("service_order_parcels", build_service_order_parcel_row(parcel))

	ensure_cost_charge_rows_for_parcels(job, parcel_rows)
	job.reload()
	service_order.service_order_charges = []
	append_parcel_charge_rows(service_order, parcel_rows)
	link_cost_charge_rows_for_parcels(service_order, job)

	milestones = get_road_transport_milestones_for_service_order(service_order)
	service_order.tracking_milestones = render_tracking_milestones_html(milestones)
	service_order.scope_of_work = build_scope_of_work(
		job, "Road Transport", transporter, parcel_rows=parcel_rows
	)
	service_order.service_instruction = get_service_instruction(
		transporter, "Road Transport", job, parcel_rows=parcel_rows
	)


def link_parcels_to_service_order(job, service_order):
	refs = {
		row.cargo_parcel_reference
		for row in service_order.get("service_order_parcels") or []
		if row.get("cargo_parcel_reference")
	}
	changed = False
	for parcel in job.get("cargo_parcel_details") or []:
		if parcel.name in refs:
			parcel.service_order_reference = service_order.name
			changed = True
	if changed:
		job.save(ignore_permissions=True)


def unlink_parcels_from_service_order(job, service_order_name):
	changed = False
	for parcel in job.get("cargo_parcel_details") or []:
		if parcel.get("service_order_reference") == service_order_name:
			parcel.service_order_reference = None
			changed = True
	if changed:
		job.save(ignore_permissions=True)


def refresh_road_transport_service_order(doc, job):
	parcel_refs = [row.cargo_parcel_reference for row in doc.get("service_order_parcels") or []]
	if not parcel_refs:
		frappe.throw(_("No linked cargo parcels found on this Service Order."))

	parcel_rows = get_parcels_by_names(job, parcel_refs, transporter=doc.supplier)
	doc.service_order_parcels = []
	for parcel in parcel_rows:
		doc.append("service_order_parcels", build_service_order_parcel_row(parcel))

	milestones = get_road_transport_milestones_for_service_order(doc)
	doc.tracking_milestones = render_tracking_milestones_html(milestones)
	doc.scope_of_work = build_scope_of_work(job, "Road Transport", doc.supplier, parcel_rows=parcel_rows)
	doc.service_instruction = get_service_instruction(
		doc.supplier, "Road Transport", job, parcel_rows=parcel_rows
	)


def _format_milestone_html(labels):
	if not labels:
		return ""
	items = "".join(f"{label}<br>" for label in labels)
	return (
		f"<div style='margin-top:4px;font-size:13px;line-height:1.1;'>"
		f"<strong>Key Milestones:</strong><br>{items}</div>"
	)


def _render_two_column_scope(left_rows, right_rows, milestone_html=""):
	def _column(items):
		if not items:
			return ""
		return "".join(f"{label}: {value}<br>" for label, value in items)

	return (
		f"<table style='width:100%;border-collapse:collapse;'>"
		f"<tr>"
		f"<td style='width:50%;vertical-align:top;padding:2px 8px 2px 0;line-height:1.1;font-size:13px;'>"
		f"{_column(left_rows)}</td>"
		f"<td style='width:50%;vertical-align:top;padding:2px 0;line-height:1.1;font-size:13px;'>"
		f"{_column(right_rows)}</td>"
		f"</tr></table>{milestone_html or ''}"
	)


def populate_job_context(service_order, job):
	service_order.company = job.company
	service_order.currency = job.currency
	service_order.bl_number = job.get("bl_number")
	service_order.shipping_line = job.get("shipping_line")
	service_order.cargo_count = job.get("cargo_count")
	service_order.port_of_loading = job.get("port_of_loading")
	service_order.port_of_discharge = job.get("port_of_discharge")
	service_order.destination = job.get("destination")
	service_order.cargo_description = job.get("cargo_description")
	service_order.direction = job.get("direction")
	service_order.shipment_mode = job.get("shipment_mode")
	service_order.incoterms = job.get("incoterms")


def append_charge_rows(service_order, charge_rows, from_costing=False):
	for row in charge_rows:
		service_order.append("service_order_charges", {
			"charge": row.charge,
			"description": row.description or row.charge,
			"qty": row.qty or 1,
			"buy_rate": row.buy_rate or 0,
			"cost_charge_row": None if from_costing else row.name,
		})


def calculate_charge_amounts(service_order):
	total = 0
	for row in service_order.get("service_order_charges") or []:
		row.amount = flt(row.qty or 1) * flt(row.buy_rate or 0)
		total += row.amount
	service_order.total_amount = total


def validate_active_duplicate(forwarding_job, service_module, supplier, exclude_name=None):
	filters = {
		"forwarding_job_reference": forwarding_job,
		"service_module": service_module,
		"supplier": supplier,
		"docstatus": 1,
	}
	if exclude_name:
		filters["name"] = ["!=", exclude_name]

	existing = frappe.db.get_value("Service Order", filters, "name")
	if existing:
		frappe.throw(
			_("An active Service Order ({0}) already exists for {1} / {2} on this job.")
			.format(existing, service_module, supplier)
		)


def link_cost_charges_to_service_order(job, service_order):
	for so_row in service_order.get("service_order_charges") or []:
		if not so_row.cost_charge_row:
			continue
		for cost_row in job.get("forwarding_cost_charges") or []:
			if cost_row.name == so_row.cost_charge_row:
				cost_row.is_ordered = 1
				cost_row.service_order_reference = service_order.name
				break
	job.save(ignore_permissions=True)


def unlink_cost_charges_from_service_order(job, service_order_name):
	changed = False
	for cost_row in job.get("forwarding_cost_charges") or []:
		if cost_row.get("service_order_reference") == service_order_name:
			cost_row.is_ordered = 0
			cost_row.service_order_reference = None
			changed = True
	if changed:
		job.save(ignore_permissions=True)


def validate_cost_rows_have_submitted_service_order(selected_rows):
	from freightmas.forwarding_service.utils.service_order_settings import service_order_required_before_pi

	if not service_order_required_before_pi():
		return

	missing = []
	for row in selected_rows:
		reference = row.get("service_order_reference")
		if not reference:
			missing.append(row.name)
			continue
		docstatus = frappe.db.get_value("Service Order", reference, "docstatus")
		if docstatus != 1:
			missing.append(row.name)

	if missing:
		frappe.throw(
			_("A submitted Service Order is required before creating a Purchase Invoice. "
			  "Missing or invalid Service Order for charge row(s): {0}")
			.format(", ".join(missing))
		)
