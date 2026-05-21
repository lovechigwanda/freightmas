import frappe
from frappe.utils import getdate, nowdate


def find_rate_card_header(shipping_line, port, direction, as_of_date=None):
	"""
	Find the best matching DND Storage Rate Card header for a job.

	Priority (best → worst):
	  1. port-specific  + direction-specific
	  2. port-specific  + direction blank (applies to both)
	  3. port = blank   + direction-specific
	  4. port = blank   + direction blank  (most generic)

	Returns a frappe._dict with card fields, or None.
	"""
	if not shipping_line:
		return None

	today = getdate(as_of_date or nowdate())

	candidates = frappe.get_all(
		"DND Storage Rate Card",
		filters={"shipping_line": shipping_line, "is_active": 1},
		fields=["name", "port", "direction", "currency", "valid_from", "valid_to",
		        "dnd_free_days", "storage_free_days"],
	)

	# Filter by validity and bucket into priority groups
	buckets = {1: [], 2: [], 3: [], 4: []}

	for card in candidates:
		vf = getdate(card.valid_from) if card.valid_from else None
		vt = getdate(card.valid_to) if card.valid_to else None
		if vf and today < vf:
			continue
		if vt and today > vt:
			continue

		card_port = card.port or ""
		card_dir = card.direction or ""
		job_port = port or ""
		job_dir = direction or ""

		if card_port == job_port and card_dir == job_dir:
			buckets[1].append(card)
		elif card_port == job_port and not card_dir:
			buckets[2].append(card)
		elif not card_port and card_dir == job_dir:
			buckets[3].append(card)
		elif not card_port and not card_dir:
			buckets[4].append(card)

	for priority in (1, 2, 3, 4):
		if buckets[priority]:
			return buckets[priority][0]

	return None


def find_container_rate(card_name, container_type):
	"""
	Look up the per-container-type rates from the rate card's child table.
	Returns a dict {dnd_rate_per_day, storage_rate_per_day, storage_rate_per_day_hazardous},
	or zeros if not found.
	"""
	row = frappe.db.get_value(
		"DND Storage Rate Card Item",
		{"parent": card_name, "container_type": container_type},
		["dnd_rate_per_day", "storage_rate_per_day", "storage_rate_per_day_hazardous"],
		as_dict=True,
	)
	if row:
		return row
	return frappe._dict(dnd_rate_per_day=0, storage_rate_per_day=0, storage_rate_per_day_hazardous=0)


def calculate_dnd_days(discharge_date, pickup_date, dnd_free_days, direction):
	"""
	Returns (total_days, chargeable_days).
	Import: discharge_date → pickup_date (gate-out from terminal).
	Export: discharge_date is pick-up-empty date, pickup_date is loaded-on-vessel date.
	Falls back to today if end date is not set.
	"""
	if not discharge_date:
		return 0, 0

	start = getdate(discharge_date)
	end = getdate(pickup_date) if pickup_date else getdate(nowdate())

	if end < start:
		return 0, 0

	total = (end - start).days + 1
	chargeable = max(0, total - int(dnd_free_days or 0))
	return total, chargeable


def calculate_storage_days(discharge_date, terminal_out_date, storage_free_days):
	"""
	Returns (total_days, chargeable_days).
	Storage clock starts at discharge, ends when container leaves terminal.
	Falls back to today if terminal_out_date is not set.
	"""
	if not discharge_date:
		return 0, 0

	start = getdate(discharge_date)
	end = getdate(terminal_out_date) if terminal_out_date else getdate(nowdate())

	if end < start:
		return 0, 0

	total = (end - start).days + 1
	chargeable = max(0, total - int(storage_free_days or 0))
	return total, chargeable


def calculate_dnd_storage_for_job(forwarding_job_doc):
	"""
	Recalculates all DND & Storage rows for a Forwarding Job document.
	Updates each row in-place and returns (total_dnd, total_storage, total_combined).
	"""
	direction = forwarding_job_doc.direction
	shipping_line = forwarding_job_doc.get("shipping_line")
	port_of_discharge = forwarding_job_doc.get("port_of_discharge")
	today = nowdate()

	# Find the rate card header once for the whole job — same SL + port for all containers
	header = find_rate_card_header(shipping_line, port_of_discharge, direction, today)

	# Fallback free days from shipping line master if no rate card found
	fallback_free_days = 0
	if not header and shipping_line:
		sl = frappe.get_cached_value(
			"Shipping Line", shipping_line,
			["free_days_import", "free_days_export"],
			as_dict=True,
		)
		if sl:
			fallback_free_days = sl.free_days_import if direction == "Import" else (sl.free_days_export or 0)

	total_dnd = 0
	total_storage = 0

	for row in (forwarding_job_doc.forwarding_dnd_storage_details or []):
		if header:
			row.rate_card = header.name
			row.rate_card_currency = header.currency
			row.dnd_free_days = header.dnd_free_days or 0
			row.storage_free_days = header.storage_free_days or 0

			# Per-container rates from child table
			rates = find_container_rate(header.name, row.container_type)
			row.dnd_rate_per_day = rates.dnd_rate_per_day or 0
			# Use hazardous storage rate when cargo is hazardous and a non-zero rate exists
			hazardous_storage_rate = rates.storage_rate_per_day_hazardous or 0
			if row.get("is_hazardous") and hazardous_storage_rate:
				row.storage_rate_per_day = hazardous_storage_rate
			else:
				row.storage_rate_per_day = rates.storage_rate_per_day or 0
		else:
			row.rate_card = None
			row.rate_card_currency = None
			row.dnd_free_days = fallback_free_days
			row.storage_free_days = fallback_free_days
			row.dnd_rate_per_day = 0
			row.storage_rate_per_day = 0

		# DND days — returnable containers end at empty_return_date; others at gate_out_date
		dnd_end = row.empty_return_date if row.to_be_returned else row.gate_out_date
		total_dnd_days, chargeable_dnd = calculate_dnd_days(
			row.discharge_date, dnd_end, row.dnd_free_days, direction
		)
		row.total_dnd_days = total_dnd_days
		row.chargeable_dnd_days = chargeable_dnd
		row.estimated_dnd_cost = chargeable_dnd * (row.dnd_rate_per_day or 0)

		# Storage days — always ends at gate_out_date (when container leaves terminal)
		total_storage_days, chargeable_storage = calculate_storage_days(
			row.discharge_date, row.gate_out_date, row.storage_free_days
		)
		row.total_storage_days = total_storage_days
		row.chargeable_storage_days = chargeable_storage
		row.estimated_storage_cost = chargeable_storage * (row.storage_rate_per_day or 0)

		row.total_container_cost = (row.estimated_dnd_cost or 0) + (row.estimated_storage_cost or 0)

		total_dnd += row.estimated_dnd_cost or 0
		total_storage += row.estimated_storage_cost or 0

	return total_dnd, total_storage, total_dnd + total_storage
