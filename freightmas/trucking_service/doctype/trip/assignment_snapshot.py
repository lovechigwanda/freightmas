# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Copy truck assignment onto Trip so Truck master changes cannot rewrite history.

Trip.truck is already a stored Link. The bug is live fetch_from on driver / horse /
trailer / warehouse: Frappe's update_linked_doctypes copies the Truck's current
values onto every historical Trip when the Truck is saved.

These helpers copy values when the trip's truck is set or changed, and leave
them alone afterwards. Driver can still be overridden on the trip itself.
"""


def _get(obj, key, default=None):
	if obj is None:
		return default
	getter = getattr(obj, "get", None)
	if callable(getter):
		value = getter(key)
		return default if value is None else value
	return getattr(obj, key, default)


def _set_if(trip, field, value):
	setattr(trip, field, value)


def _is_empty(value):
	return value is None or value == ""


def apply_truck_assignment_snapshot(
	trip,
	truck,
	truck_changed,
	driver_explicitly_set=False,
	trailer_explicitly_set=False,
):
	"""Snapshot horse, trailer, warehouse, and default driver from Truck onto Trip.

	When *truck_changed* is True, vehicle fields are copied from the new truck.
	Driver and trailer are copied unless the caller already set them on this save.

	When *truck_changed* is False, only empty trip fields are filled. Existing
	values are never overwritten — this is what keeps history stable when the
	Truck master later changes driver or trailer.
	"""
	if not truck:
		return trip

	if truck_changed:
		_set_if(trip, "horse", _get(truck, "horse"))
		_set_if(trip, "s_warehouse", _get(truck, "warehouse"))
		if not trailer_explicitly_set:
			_set_if(trip, "trailer", _get(truck, "assigned_trailer"))
		if not driver_explicitly_set:
			_set_if(trip, "driver", _get(truck, "assigned_driver"))
		return trip

	if _is_empty(_get(trip, "horse")):
		_set_if(trip, "horse", _get(truck, "horse"))
	if _is_empty(_get(trip, "trailer")):
		_set_if(trip, "trailer", _get(truck, "assigned_trailer"))
	if _is_empty(_get(trip, "s_warehouse")):
		_set_if(trip, "s_warehouse", _get(truck, "warehouse"))
	if _is_empty(_get(trip, "driver")):
		_set_if(trip, "driver", _get(truck, "assigned_driver"))
	return trip


def resolve_legacy_driver_value(stored_driver, truck_assigned_driver=None, driver_ids=None, full_name_to_ids=None):
	"""Map a Trip.driver value that may be a Driver id or a full_name string.

	Returns (driver_id, fallback_display_name).
	*fallback_display_name* is set when the stored value looks like a person's
	name and could not be matched to a Driver, so it can be kept on driver_name.
	"""
	driver_ids = driver_ids or set()
	full_name_to_ids = full_name_to_ids or {}
	stored = (stored_driver or "").strip()

	if stored and stored in driver_ids:
		return stored, None

	if stored:
		matches = list(full_name_to_ids.get(stored) or [])
		if len(matches) == 1:
			return matches[0], stored
		if len(matches) > 1 and truck_assigned_driver in matches:
			return truck_assigned_driver, stored
		return None, stored

	if truck_assigned_driver and truck_assigned_driver in driver_ids:
		return truck_assigned_driver, None

	return None, None
