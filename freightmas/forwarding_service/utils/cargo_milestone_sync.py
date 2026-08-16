# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Bridge API port dates on Cargo Parcel Details to trucking milestone checkboxes."""


def apply_parcel_loading_master_defaults(doc, row):
	"""Copy job-level Loading Master / trucking service defaults onto a parcel row."""
	if doc.get("is_trucking_required"):
		row.is_truck_required = 1
	elif doc.get("is_trucking_required") is not None and not row.is_truck_required:
		row.is_truck_required = 0

	if doc.get("road_freight_route") and not row.get("road_freight_route"):
		row.road_freight_route = doc.road_freight_route
	if doc.get("offloadiing_address") and not row.get("cargo_offloading_address"):
		row.cargo_offloading_address = doc.offloadiing_address
	if doc.get("loading_address") and not row.get("cargo_loading_address"):
		row.cargo_loading_address = doc.loading_address


def sync_loaded_milestone_from_gate_out(cargo):
	"""Gate-out date from API → Loaded milestone when already booked."""
	if not cargo.get("is_truck_required") or not cargo.get("gate_out_date"):
		return False
	if not cargo.get("is_booked"):
		return False

	source = cargo.get("loaded_milestone_source") or ""
	if cargo.get("is_loaded") and source == "Manual":
		return False
	if cargo.get("is_loaded") and cargo.get("loaded_on_date") and source not in ("", "API"):
		return False

	cargo.is_loaded = 1
	cargo.loaded_on_date = cargo.gate_out_date
	cargo.loaded_milestone_source = "API"
	return True


def sync_return_milestone_from_empty_return(cargo):
	"""Empty return date from API → Returned milestone when already offloaded."""
	if not cargo.get("to_be_returned") or not cargo.get("empty_return_date"):
		return False
	if not cargo.get("is_offloaded"):
		return False

	source = cargo.get("return_milestone_source") or ""
	if cargo.get("is_returned") and source == "Manual":
		return False
	if cargo.get("is_returned") and cargo.get("returned_on_date") and source not in ("", "API"):
		return False

	cargo.is_returned = 1
	cargo.returned_on_date = cargo.empty_return_date
	cargo.return_milestone_source = "API"
	return True


def sync_cargo_milestones_from_port_dates(cargo):
	"""Run all port-date → milestone bridges for one cargo row."""
	loaded = sync_loaded_milestone_from_gate_out(cargo)
	returned = sync_return_milestone_from_empty_return(cargo)
	return loaded or returned


def is_cargo_returned(cargo):
	"""True when return is complete via trucking milestone or API port date."""
	return bool(cargo.get("is_returned") or cargo.get("empty_return_date"))
