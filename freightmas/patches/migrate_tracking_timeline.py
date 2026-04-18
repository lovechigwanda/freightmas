"""Migrate Forwarding Tracking rows to unified Forwarding Tracking Event timeline.

Copies all existing manual tracking entries from the old `forwarding_tracking`
child table to the new `tracking_timeline` child table on Forwarding Job.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Forwarding Tracking"):
		return

	if not frappe.db.table_exists("Forwarding Tracking Event"):
		return

	# Check if there are any old rows to migrate
	old_rows = frappe.db.sql(
		"""
		SELECT name, parent, parentfield, comment, updated_by, updated_on, idx
		FROM `tabForwarding Tracking`
		WHERE parenttype = 'Forwarding Job'
		ORDER BY parent, idx
		""",
		as_dict=True,
	)

	if not old_rows:
		return

	# Check which parents already have timeline rows (avoid re-running)
	existing_parents = set(
		frappe.db.sql_list(
			"""
			SELECT DISTINCT parent
			FROM `tabForwarding Tracking Event`
			WHERE parenttype = 'Forwarding Job' AND source = 'Manual'
			"""
		)
	)

	# Group by parent to assign correct idx values
	from collections import defaultdict

	rows_by_parent = defaultdict(list)
	for row in old_rows:
		if row.parent not in existing_parents:
			rows_by_parent[row.parent].append(row)

	if not rows_by_parent:
		frappe.logger().info("Tracking migration: no new rows to migrate (already done)")
		return

	migrated = 0
	for parent, rows in rows_by_parent.items():
		# Get the current max idx in the new table for this parent
		max_idx = frappe.db.sql(
			"""
			SELECT COALESCE(MAX(idx), 0)
			FROM `tabForwarding Tracking Event`
			WHERE parent = %s AND parenttype = 'Forwarding Job'
			""",
			parent,
		)[0][0]

		for i, row in enumerate(rows, start=1):
			frappe.db.sql(
				"""
				INSERT INTO `tabForwarding Tracking Event`
				(name, parent, parenttype, parentfield, idx, source, event, date, updated_by, creation, modified, modified_by, owner)
				VALUES (%(name)s, %(parent)s, 'Forwarding Job', 'tracking_timeline', %(idx)s,
						'Manual', %(event)s, %(date)s, %(updated_by)s, %(date)s, %(date)s, %(updated_by)s, %(updated_by)s)
				""",
				{
					"name": frappe.generate_hash(length=10),
					"parent": parent,
					"idx": max_idx + i,
					"event": row.comment,
					"date": row.updated_on,
					"updated_by": row.updated_by or "Administrator",
				},
			)
			migrated += 1

	frappe.db.commit()
	frappe.logger().info(f"Tracking migration: migrated {migrated} rows across {len(rows_by_parent)} jobs")
