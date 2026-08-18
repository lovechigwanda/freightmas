import frappe


def execute():
	"""Align job-level Trucking Service with parcel-level trucking flags."""
	enabled_jobs = _enable_trucking_service_where_parcels_require_it()
	cleared_stale = _clear_stale_trucks_required()
	frappe.db.commit()
	return {"enabled_jobs": enabled_jobs, "cleared_stale_trucks_required": cleared_stale}


def _enable_trucking_service_where_parcels_require_it():
	job_names = frappe.db.sql(
		"""
		SELECT DISTINCT cp.parent
		FROM `tabCargo Parcel Details` cp
		INNER JOIN `tabForwarding Job` fj ON fj.name = cp.parent
		WHERE cp.is_truck_required = 1
		  AND IFNULL(fj.is_trucking_required, 0) = 0
		  AND fj.docstatus < 2
		""",
		pluck=True,
	)

	for name in job_names:
		frappe.db.set_value(
			"Forwarding Job",
			name,
			"is_trucking_required",
			1,
			update_modified=False,
		)

	return len(job_names)


def _clear_stale_trucks_required():
	return frappe.db.sql(
		"""
		UPDATE `tabForwarding Job` fj
		SET trucks_required = ''
		WHERE IFNULL(fj.trucks_required, '') != ''
		  AND fj.docstatus < 2
		  AND NOT EXISTS (
			SELECT 1
			FROM `tabCargo Parcel Details` cp
			WHERE cp.parent = fj.name
			  AND cp.is_truck_required = 1
		  )
		"""
	)
