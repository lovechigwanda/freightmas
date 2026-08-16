import frappe

from freightmas.forwarding_service.utils.service_order import get_service_instruction


def execute():
	orders = frappe.get_all(
		"Service Order",
		filters={
			"forwarding_job_reference": ["is", "set"],
			"service_module": ["is", "set"],
			"supplier": ["is", "set"],
			"service_instruction": ["is", "not set"],
		},
		fields=["name", "forwarding_job_reference", "service_module", "supplier"],
	)

	updated = 0
	for row in orders:
		job = frappe.get_doc("Forwarding Job", row.forwarding_job_reference)
		instruction = get_service_instruction(row.supplier, row.service_module, job)
		frappe.db.set_value(
			"Service Order",
			row.name,
			"service_instruction",
			instruction,
			update_modified=False,
		)
		updated += 1

	frappe.db.commit()
	return updated
