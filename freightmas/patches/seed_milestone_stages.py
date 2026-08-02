# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Data migration (2026-08-02): introduce milestone Stages for summarized
client reports.

1. Create the Customer "Client Report Milestone Detail" override custom field.
2. Seed default Milestone Stage records for Port Clearance and tag each of the
   15 Port Clearance Milestone Definitions with its stage.
3. Backfill the snapshotted stage / stage_sequence on existing Job Milestone
   Progress rows (Port Clearance) by joining milestone_code -> its definition's
   stage, so jobs created before this change also summarize correctly.

Idempotent: re-running skips stages/fields that already exist and only fills in
missing snapshot values, so it is safe if it runs more than once.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# Port Clearance stages, in display order, and the milestone codes each groups.
PORT_CLEARANCE_STAGES = [
	("Documentation", 1, [
		"PC_PREALERT_RECEIVED",
		"PC_ENDORSEMENT_LETTER",
		"PC_COMMERCIAL_INVOICE",
		"PC_BILL_OF_LADING",
		"PC_PACKING_LIST",
	]),
	("Shipping Line", 2, [
		"PC_SL_INVOICE_REQUESTED",
		"PC_SL_INVOICE_RECEIVED",
		"PC_SL_INVOICE_PAID",
		"PC_SL_BL_RELEASED",
	]),
	("Customs", 3, [
		"PC_CUSTOMS_ENTRY_LODGED",
		"PC_CUSTOMS_CLEARANCE_COMPLETED",
	]),
	("Port Release", 4, [
		"PC_DO_REQUESTED",
		"PC_DO_RECEIVED",
		"PC_PORT_RELEASE_LODGED",
		"PC_PORT_RELEASE_CONFIRMED",
	]),
]


def execute():
	_create_customer_override_field()

	if not frappe.db.exists("DocType", "Milestone Stage"):
		return

	# 1. Create the Milestone Stage records + tag each definition.
	code_to_stage = {}  # milestone_code -> (stage_name, stage_sequence)
	for stage_name, stage_seq, codes in PORT_CLEARANCE_STAGES:
		stage_doc = _ensure_stage(stage_name, "Port Clearance", stage_seq)
		for code in codes:
			code_to_stage[code] = (stage_name, stage_seq)
			def_name = frappe.db.get_value("Milestone Definition", {"milestone_code": code}, "name")
			if def_name:
				frappe.db.set_value("Milestone Definition", def_name, "stage", stage_doc, update_modified=False)

	# 2. Backfill the snapshot on existing Job Milestone Progress rows. Editing
	# these rows directly at the DB layer intentionally bypasses Forwarding
	# Job's milestone guards - this is a deliberate admin backfill, not UI use.
	rows = frappe.get_all(
		"Job Milestone Progress",
		filters={"service_module": "Port Clearance"},
		fields=["name", "milestone_code", "stage"],
	)
	for row in rows:
		if row.stage:
			continue  # already has a snapshot - don't overwrite
		mapping = code_to_stage.get(row.milestone_code)
		if not mapping:
			continue
		stage_name, stage_seq = mapping
		frappe.db.set_value(
			"Job Milestone Progress", row.name,
			{"stage": stage_name, "stage_sequence": stage_seq},
			update_modified=False,
		)

	frappe.db.commit()


def _ensure_stage(stage_name, service_module, stage_sequence):
	"""Return the name of the Milestone Stage, creating it if missing."""
	existing = frappe.db.get_value(
		"Milestone Stage",
		{"stage_name": stage_name, "service_module": service_module},
		"name",
	)
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Milestone Stage",
		"stage_name": stage_name,
		"service_module": service_module,
		"stage_sequence": stage_sequence,
		"is_active": 1,
	}).insert(ignore_permissions=True)
	return doc.name


def _create_customer_override_field():
	create_custom_fields(
		{
			"Customer": [
				{
					"fieldname": "custom_client_report_milestone_detail",
					"label": "Client Report Milestone Detail",
					"fieldtype": "Select",
					"options": "Use Default\nFull Milestones\nStage Summary",
					"default": "Use Default",
					"insert_after": "customer_type",
					"description": "Overrides the FreightMas Settings default for this customer's tracking reports. 'Stage Summary' shows the current stage and overall progress instead of every milestone.",
					"translatable": 0,
				}
			]
		},
		update=True,
	)
	frappe.db.commit()
