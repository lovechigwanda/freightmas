# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Convert Trip.driver from a fetched full_name string to a Driver link.

Trip.driver used to be a Read Only fetch_from of Truck.assigned_driver_name.
That value was overwritten whenever the Truck master changed driver. After the
doctype change, driver is a Link to Driver and driver_name holds the display
name snapshot.
"""

import frappe

from freightmas.trucking_service.doctype.trip.assignment_snapshot import resolve_legacy_driver_value


def execute():
	if not frappe.db.table_exists("Trip"):
		return

	driver_rows = frappe.get_all("Driver", fields=["name", "full_name"]) if frappe.db.table_exists("Driver") else []
	driver_ids = {row.name for row in driver_rows}
	full_name_to_ids = {}
	driver_full_names = {row.name: row.full_name for row in driver_rows}
	for row in driver_rows:
		if row.full_name:
			full_name_to_ids.setdefault(row.full_name.strip(), []).append(row.name)

	trips = frappe.get_all("Trip", fields=["name", "driver", "truck", "driver_name"])
	for trip in trips:
		truck_driver = None
		if trip.truck and frappe.db.exists("Truck", trip.truck):
			truck_driver = frappe.db.get_value("Truck", trip.truck, "assigned_driver")

		driver_id, fallback_name = resolve_legacy_driver_value(
			trip.driver,
			truck_assigned_driver=truck_driver,
			driver_ids=driver_ids,
			full_name_to_ids=full_name_to_ids,
		)

		updates = {}
		if driver_id:
			updates["driver"] = driver_id
			updates["driver_name"] = driver_full_names.get(driver_id) or fallback_name or trip.driver_name
		else:
			if trip.driver and trip.driver not in driver_ids:
				updates["driver"] = None
			if fallback_name and not trip.driver_name:
				updates["driver_name"] = fallback_name

		if not updates:
			continue

		frappe.db.set_value("Trip", trip.name, updates, update_modified=False)
