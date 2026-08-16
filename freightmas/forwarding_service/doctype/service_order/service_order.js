// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Order', {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.purchase_invoice_reference) {
			frm.add_custom_button(__('Create Purchase Invoice'), () => {
				frappe.call({
					method: 'freightmas.forwarding_service.doctype.service_order.service_order.create_purchase_invoice_from_service_order',
					args: { docname: frm.doc.name },
					callback(r) {
						if (r.message) {
							frappe.set_route('Form', 'Purchase Invoice', r.message);
						}
					},
				});
			}, __('Create'));
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__('Service Order'), () => {
				window.open(
					`/printview?doctype=Service%20Order&name=${encodeURIComponent(frm.doc.name)}&format=Service%20Order`,
					'_blank'
				);
			}, __('View'));
		}

		if (frm.doc.docstatus === 0 && frm.doc.forwarding_job_reference && frm.doc.service_module && frm.doc.supplier) {
			frm.add_custom_button(__('Refresh Scope from Job'), () => {
				frappe.call({
					method: 'freightmas.forwarding_service.doctype.service_order.service_order.refresh_service_order_scope',
					args: { docname: frm.doc.name },
					freeze: true,
					freeze_message: __('Refreshing scope from job...'),
					callback(r) {
						if (r.exc) {
							return;
						}
						_apply_scope_context(frm, r.message || {}, true);
						if (r.message?.tracking_milestones && frm.fields_dict.tracking_milestones) {
							frm.set_value('tracking_milestones', r.message.tracking_milestones);
						}
						frm.reload_doc();
						frappe.show_alert({ message: __('Scope refreshed from job'), indicator: 'green' });
					},
				});
			});
		}

		if (!frm.is_new() && frm.doc.docstatus === 0 && frm.doc.forwarding_job_reference
			&& frm.doc.service_module && frm.doc.supplier && !frm.doc.service_instruction) {
			_backfill_service_instruction(frm);
		}
	},

	forwarding_job_reference(frm) {
		if (frm.doc.forwarding_job_reference && frm.doc.service_module && frm.doc.supplier) {
			_populate_scope_from_job(frm);
		}
	},

	service_module(frm) {
		if (frm.doc.forwarding_job_reference && frm.doc.service_module) {
			_load_supplier_defaults(frm);
		}
	},

	supplier(frm) {
		if (frm.doc.forwarding_job_reference && frm.doc.service_module && frm.doc.supplier) {
			_populate_scope_from_job(frm);
		}
	},
});

function _load_supplier_defaults(frm) {
	frappe.call({
		method: 'freightmas.forwarding_service.doctype.service_order.service_order.get_service_order_creation_context',
		args: {
			docname: frm.doc.forwarding_job_reference,
			service_module: frm.doc.service_module,
		},
		callback(r) {
			if (!r.message) return;
			if (!frm.doc.supplier && r.message.default_supplier) {
				frm.set_value('supplier', r.message.default_supplier);
			}
			_apply_scope_context(frm, r.message);
		},
	});
}

function _populate_scope_from_job(frm) {
	frappe.call({
		method: 'freightmas.forwarding_service.doctype.service_order.service_order.get_service_order_creation_context',
		args: {
			docname: frm.doc.forwarding_job_reference,
			service_module: frm.doc.service_module,
			supplier: frm.doc.supplier,
		},
		callback(r) {
			if (r.message) {
				_apply_scope_context(frm, r.message);
			}
		},
	});
}

function _apply_scope_context(frm, context, force = false) {
	if (context.scope_of_work && (force || !frm.doc.scope_of_work)) {
		frm.set_value('scope_of_work', context.scope_of_work);
	}
	if (context.service_instruction && (force || !frm.doc.service_instruction)) {
		frm.set_value('service_instruction', context.service_instruction);
	}
}

function _backfill_service_instruction(frm) {
	frappe.call({
		method: 'freightmas.forwarding_service.doctype.service_order.service_order.refresh_service_order_scope',
		args: { docname: frm.doc.name },
		callback(r) {
			if (!r.message?.service_instruction) {
				return;
			}
			_apply_scope_context(frm, r.message, true);
			frm.reload_doc();
		},
	});
}
