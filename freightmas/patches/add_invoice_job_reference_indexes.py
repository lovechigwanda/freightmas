# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Add database indexes on the invoice -> job reference custom fields.

The Command Center dashboards aggregate revenue/cost by joining Sales Invoice /
Purchase Invoice to each central job doctype on a custom link column
(forwarding_job_reference, clearing_job_reference, ...). Frappe does not
auto-index custom Link fields, so without these the SUM(base_grand_total)
GROUP BY <ref> queries table-scan the invoice tables. These single-column
indexes make the executive-overview fan-out and every module finance view cheap.

Idempotent and defensive: skips any column that does not exist on a given
doctype, and add_index itself no-ops if the index is already present.
"""

import frappe


REF_FIELDS = [
	"forwarding_job_reference",
	"clearing_job_reference",
	"border_clearing_job_reference",
	"road_freight_job_reference",
	"trip_reference",
	"warehouse_job_reference",
]


def execute():
	for doctype in ("Sales Invoice", "Purchase Invoice"):
		existing_columns = set(frappe.db.get_table_columns(doctype))
		for field in REF_FIELDS:
			if field not in existing_columns:
				continue
			# Index name kept well under MySQL's 64-char limit.
			frappe.db.add_index(doctype, [field], index_name=f"idx_{field}")
