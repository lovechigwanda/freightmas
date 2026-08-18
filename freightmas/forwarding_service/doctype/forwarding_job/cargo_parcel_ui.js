// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
// Cargo Parcel Details — milestone bridges, trucking sync, row editor helpers
// Tabs are native Frappe Tab Break fields on the Cargo Parcel Details doctype.

const PARCEL_MILESTONE_REFRESH_FIELDS = [
	'is_booked', 'is_loaded', 'is_offloaded', 'is_returned', 'is_completed',
	'booked_on_date', 'loaded_on_date', 'offloaded_on_date', 'returned_on_date', 'completed_on_date',
	'loaded_milestone_source', 'return_milestone_source',
];

function get_cargo_parcel_grid_row(frm, cdn) {
	return frm.fields_dict.cargo_parcel_details?.grid?.grid_rows_by_docname?.[cdn];
}

function get_active_parcel_tab_fieldname(grid_row) {
	const active_tab = grid_row?.grid_form?.active_tab;
	if (active_tab?.df?.fieldname) {
		return active_tab.df.fieldname;
	}
	const tab = grid_row?.grid_form?.layout?.tabs?.find(
		t => t.tab_link?.find('.nav-link').hasClass('active')
	);
	return tab?.df?.fieldname || null;
}

function restore_parcel_row_tab(grid_row, tab_fieldname) {
	if (!grid_row?.grid_form?.layout || !tab_fieldname) return;
	const tab = grid_row.grid_form.layout.tabs?.find(t => t.df.fieldname === tab_fieldname);
	tab?.set_active();
}

function refresh_cargo_parcel_row(frm, cdn, fieldnames) {
	const grid_row = get_cargo_parcel_grid_row(frm, cdn);
	if (!grid_row) {
		frm.refresh_field('cargo_parcel_details');
		return;
	}

	const active_tab = get_active_parcel_tab_fieldname(grid_row);

	if (fieldnames?.length) {
		fieldnames.forEach((fieldname) => grid_row.refresh_field(fieldname));
	} else {
		grid_row.grid_form?.layout?.refresh(grid_row.doc);
		restore_parcel_row_tab(grid_row, active_tab);
	}

	setup_parcel_row_helpers(frm, 'Cargo Parcel Details', cdn);
	show_milestone_bridge_hints(frm, 'Cargo Parcel Details', cdn);
}

function populate_parcel_row_defaults(frm, cdt, cdn) {
	if (frm.doc.is_trucking_required !== undefined) {
		frappe.model.set_value(cdt, cdn, 'is_truck_required', frm.doc.is_trucking_required ? 1 : 0);
	}
	if (frm.doc.road_freight_route) {
		frappe.model.set_value(cdt, cdn, 'road_freight_route', frm.doc.road_freight_route);
	}
	if (frm.doc.offloadiing_address) {
		frappe.model.set_value(cdt, cdn, 'cargo_offloading_address', frm.doc.offloadiing_address);
	}
	if (frm.doc.loading_address) {
		frappe.model.set_value(cdt, cdn, 'cargo_loading_address', frm.doc.loading_address);
	}
}

function sync_loaded_milestone_from_gate_out_client(row) {
	if (!row.is_truck_required || !row.gate_out_date || !row.is_booked) {
		return false;
	}
	if (row.is_loaded && row.loaded_milestone_source === 'Manual') {
		return false;
	}
	if (row.is_loaded && row.loaded_on_date && row.loaded_milestone_source && row.loaded_milestone_source !== 'API') {
		return false;
	}
	row.is_loaded = 1;
	row.loaded_on_date = row.gate_out_date;
	row.loaded_milestone_source = 'API';
	return true;
}

function sync_return_milestone_from_empty_return_client(row) {
	if (!row.to_be_returned || !row.empty_return_date || !row.is_offloaded) {
		return false;
	}
	if (row.is_returned && row.return_milestone_source === 'Manual') {
		return false;
	}
	if (row.is_returned && row.returned_on_date && row.return_milestone_source && row.return_milestone_source !== 'API') {
		return false;
	}
	row.is_returned = 1;
	row.returned_on_date = row.empty_return_date;
	row.return_milestone_source = 'API';
	return true;
}

function sync_cargo_milestones_from_port_dates_client(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row) return;

	const loaded = sync_loaded_milestone_from_gate_out_client(row);
	const returned = sync_return_milestone_from_empty_return_client(row);

	if (loaded || returned) {
		refresh_cargo_parcel_row(frm, cdn, [
			'is_loaded', 'loaded_on_date', 'loaded_milestone_source',
			'is_returned', 'returned_on_date', 'return_milestone_source',
		]);
		render_road_transport_progress_summary(frm);
		render_road_transport_section_badge(frm);
		render_milestone_summary(frm);
		frappe.show_alert({
			message: __('Trucking milestone(s) updated from port dates'),
			indicator: 'blue',
		}, 3);
	}
}

function show_milestone_bridge_hints(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row || !row.is_truck_required) return;

	const grid_row = frm.fields_dict.cargo_parcel_details?.grid?.grid_rows_by_docname?.[cdn];
	const wrapper = grid_row?.grid_form?.wrapper;
	if (!wrapper) return;

	wrapper.find('.parcel-milestone-hint').remove();

	const hints = [];
	if (row.gate_out_date && row.is_booked && !row.is_loaded) {
		hints.push(__('Gate-out date available — Loaded milestone will auto-complete.'));
	} else if (row.gate_out_date && !row.is_booked && !row.is_loaded) {
		hints.push(__('Gate-out date from carrier — mark Booked to auto-complete Loaded.'));
	}
	if (row.empty_return_date && row.is_offloaded && !row.is_returned) {
		hints.push(__('Empty return date available — Returned milestone will auto-complete.'));
	} else if (row.empty_return_date && !row.is_offloaded && !row.is_returned && row.to_be_returned) {
		hints.push(__('Empty return from carrier — mark Offloaded to auto-complete Returned.'));
	}
	if (row.is_loaded && row.loaded_milestone_source === 'API' && (!row.driver_name || !row.truck_reg_no)) {
		hints.push(__('Loaded date set from gate-out API — add driver/truck details before saving.'));
	}

	if (!hints.length) return;

	const html = hints.map(h => `<div class="text-muted" style="font-size: 11px; margin: 4px 0;">${frappe.utils.escape_html(h)}</div>`).join('');
	const milestone_section = wrapper.find('[data-fieldname="section_break_qomc"]');
	if (milestone_section.length) {
		milestone_section.find('.section-body').prepend(`<div class="parcel-milestone-hint">${html}</div>`);
	}

	apply_milestone_api_badges(wrapper, row);
}

function apply_milestone_api_badges(wrapper, row) {
	wrapper.find('.milestone-api-badge').remove();

	const badges = [
		{ field: 'loaded_on_date', source: row.loaded_milestone_source },
		{ field: 'returned_on_date', source: row.return_milestone_source },
	];

	badges.forEach(({ field, source }) => {
		if (source !== 'API') return;
		const control = wrapper.find(`[data-fieldname="${field}"]`);
		if (control.length && !control.find('.milestone-api-badge').length) {
			control.find('.control-input-wrapper, .like-disabled-input').first().append(
				'<span class="milestone-api-badge label label-default" style="margin-left: 6px; font-size: 10px;">API</span>'
			);
		}
	});
}

function setup_parcel_row_helpers(frm, cdt, cdn) {
	const grid_row = frm.fields_dict.cargo_parcel_details?.grid?.grid_rows_by_docname?.[cdn];
	const layout = grid_row?.grid_form?.layout;
	if (!layout?.tabs?.length) return;

	layout.tabs.forEach(tab => {
		if (tab._parcel_helpers_bound) return;
		tab._parcel_helpers_bound = true;

		tab.tab_link.find('.nav-link').on('click', () => {
			setTimeout(() => {
				if (tab.df.fieldname === 'tab_trucking') {
					add_fetch_truck_button(frm, cdt, cdn);
				}
				if (tab.df.fieldname === 'tab_progress') {
					show_milestone_bridge_hints(frm, cdt, cdn);
				}
			}, 50);
		});
	});

	// Collapse extended tracking on documents tab
	const ext_tab = layout.tabs.find(t => t.df.fieldname === 'tab_documents');
	if (ext_tab) {
		const ext_section = ext_tab.wrapper.find('[data-fieldname="extended_tracking_section"]');
		if (ext_section.length && !ext_section.hasClass('collapsed')) {
			ext_section.find('.section-head').click();
		}
	}
}

function show_trucking_update_dialog(frm) {
	if (!frm.doc.cargo_parcel_details?.length) {
		update_all_cargo_trucking_silent(frm, frm.doc.is_trucking_required ? 1 : 0);
		return;
	}

	const excluded_rows = frm.doc.cargo_parcel_details.filter(r => !r.is_truck_required);

	if (frm.doc.is_trucking_required && excluded_rows.length) {
		const dialog = new frappe.ui.Dialog({
			title: __('Update Trucking Requirement'),
			fields: [{
				fieldtype: 'HTML',
				options: `
					<p>${__('Trucking Service enabled on this job. How should cargo parcels be updated?')}</p>
					<p class="text-muted">${__('{0} parcel(s) currently excluded from trucking.', [excluded_rows.length])}</p>
				`,
			}],
			primary_action_label: __('Apply to All'),
			primary_action() {
				update_all_cargo_trucking_silent(frm, 1);
				dialog.hide();
			},
		});
		dialog.add_custom_action(__('Apply to Non-excluded Only'), () => {
			frm.doc.cargo_parcel_details.forEach(row => {
				if (row.is_truck_required) {
					frappe.model.set_value(row.doctype, row.name, 'is_truck_required', 1);
				}
			});
			frappe.show_alert({ message: __('Trucking applied to active parcels'), indicator: 'blue' }, 3);
			dialog.hide();
		});
		dialog.add_custom_action(__('Keep Current Settings'), () => dialog.hide());
		dialog.show();
		return;
	}

	if (!frm.doc.is_trucking_required && frm.doc.cargo_parcel_details.some(r =>
		r.is_booked || r.is_loaded || r.is_offloaded || r.is_completed || r.is_returned
	)) {
		frappe.confirm(
			__('Some parcels have trucking milestones. Disabling trucking on all parcels will clear those milestones. Continue?'),
			() => update_all_cargo_trucking_silent(frm, 0)
		);
		return;
	}

	update_all_cargo_trucking_silent(frm, frm.doc.is_trucking_required ? 1 : 0);
}

function update_all_cargo_trucking_silent(frm, value) {
	let updated = false;
	(frm.doc.cargo_parcel_details || []).forEach(row => {
		if (cint(row.is_truck_required) !== cint(value)) {
			frappe.model.set_value(row.doctype, row.name, 'is_truck_required', value);
			updated = true;
		}
	});
	if (updated) {
		frappe.show_alert({
			message: __('Trucking requirement updated for all cargo items'),
			indicator: 'blue',
		}, 3);
	}
}

function show_loading_address_update_dialog(frm) {
	if (!frm.doc.cargo_parcel_details?.length || !frm.doc.loading_address) return;

	const rows_with_different = frm.doc.cargo_parcel_details.filter(
		r => r.cargo_loading_address && r.cargo_loading_address !== frm.doc.loading_address
	);
	const rows_blank = frm.doc.cargo_parcel_details.filter(r => !r.cargo_loading_address);

	if (!rows_with_different.length) {
		rows_blank.forEach(row => {
			frappe.model.set_value(row.doctype, row.name, 'cargo_loading_address', frm.doc.loading_address);
		});
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __('Update Loading Addresses'),
		fields: [{
			fieldtype: 'HTML',
			options: `<p>${__('Loading address changed. Update cargo parcels?')}</p>`,
		}],
		primary_action_label: __('Update All'),
		primary_action() {
			frm.doc.cargo_parcel_details.forEach(row => {
				frappe.model.set_value(row.doctype, row.name, 'cargo_loading_address', frm.doc.loading_address);
			});
			dialog.hide();
		},
	});
	dialog.add_custom_action(__('Update Blank Only'), () => {
		rows_blank.forEach(row => {
			frappe.model.set_value(row.doctype, row.name, 'cargo_loading_address', frm.doc.loading_address);
		});
		dialog.hide();
	});
	dialog.add_custom_action(__('Keep Manual Overrides'), () => dialog.hide());
	dialog.show();
}

function prompt_enable_trucking_service(frm) {
	if (frm.doc.is_trucking_required || frm.is_new()) return;
	frappe.confirm(
		__('This cargo requires trucking but Trucking Service is not enabled on the job. Enable it?'),
		() => frm.set_value('is_trucking_required', 1)
	);
}

function open_parcel_row_on_tab(frm, row_name, tab_fieldname) {
	const grid = frm.fields_dict.cargo_parcel_details?.grid;
	if (!grid) return;

	const row_idx = (frm.doc.cargo_parcel_details || []).findIndex(r => r.name === row_name);
	if (row_idx < 0) return;

	grid.grid_rows[row_idx]?.toggle_view(true);
	setTimeout(() => {
		const grid_row = grid.grid_rows_by_docname?.[row_name];
		const layout = grid_row?.grid_form?.layout;
		const tab = layout?.tabs?.find(t => t.df.fieldname === (tab_fieldname || 'tab_progress'));
		tab?.tab_link?.find('.nav-link')?.trigger('click');
		setup_parcel_row_helpers(frm, 'Cargo Parcel Details', row_name);
		if (tab_fieldname === 'tab_trucking' || tab_fieldname === 'trucking') {
			add_fetch_truck_button(frm, 'Cargo Parcel Details', row_name);
		}
		if (!tab_fieldname || tab_fieldname === 'tab_progress' || tab_fieldname === 'progress') {
			show_milestone_bridge_hints(frm, 'Cargo Parcel Details', row_name);
		}
	}, 300);
}

frappe.ui.form.on('Forwarding Job', {
	is_trucking_required(frm) {
		show_trucking_update_dialog(frm);
	},

	loading_address(frm) {
		show_loading_address_update_dialog(frm);
	},

	fetch_revenue_from_truck_loading(frm) {
		if (!frm.doc.name) {
			frappe.msgprint(__('Please save the document first.'));
			return;
		}
		frappe.call({
			method: 'fetch_revenue_from_truck_loading',
			doc: frm.doc,
			callback(r) {
				if (r?.message !== undefined && (r.message || 0) > 0) {
					frm.reload_doc();
				}
			},
		});
	},
});

frappe.ui.form.on('Cargo Parcel Details', {
	form_render(frm, cdt, cdn) {
		setup_parcel_row_helpers(frm, cdt, cdn);
		const row = locals[cdt][cdn];
		if (row?.is_truck_required) {
			setTimeout(() => add_fetch_truck_button(frm, cdt, cdn), 300);
		}
		show_milestone_bridge_hints(frm, cdt, cdn);
	},
});
