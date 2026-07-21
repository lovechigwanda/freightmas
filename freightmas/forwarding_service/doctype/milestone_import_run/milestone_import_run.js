// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Milestone Import Run", {
	refresh(frm) {
		apply_lock_state(frm);
		setup_primary_action(frm);
		if (!["Pending", "Previewed"].includes(frm.doc.status)) {
			render_results_summary(frm);
		}
	},

	service_module(frm) {
		reset_preview(frm);
	},

	import_file(frm) {
		reset_preview(frm);
	},

	download_template(frm) {
		if (!frm.doc.service_module) {
			frappe.msgprint(__("Select a Service Module first."));
			return;
		}
		const url =
			"/api/method/freightmas.forwarding_service.milestone_import.download_import_template?service_module=" +
			encodeURIComponent(frm.doc.service_module);
		window.open(url);
	},
});

function apply_lock_state(frm) {
	const locked = frm.doc.status === "Completed";
	frm.set_df_property("import_file", "read_only", locked ? 1 : 0);
}

function reset_preview(frm) {
	frm.__milestone_preview = null;
	frm.fields_dict.import_preview.$wrapper.empty();
	setup_primary_action(frm);
}

function setup_primary_action(frm) {
	frm.page.clear_primary_action();

	if (frm.is_new() || frm.doc.status === "Completed" || !frm.doc.import_file) {
		return;
	}

	if (frm.__milestone_preview) {
		frm.page.set_primary_action(__("Apply Updates"), () => apply_updates(frm));
	} else {
		frm.page.set_primary_action(__("Preview"), () => run_preview(frm));
	}
}

function run_preview(frm) {
	frappe.call({
		doc: frm.doc,
		method: "get_preview",
		freeze: true,
		freeze_message: __("Reading file..."),
		callback(r) {
			if (!r.message) return;
			frm.__milestone_preview = r.message;
			frm.doc.status = "Previewed";
			frm.refresh_field("status");
			render_preview(frm, r.message);
			setup_primary_action(frm);
		},
	});
}

function apply_updates(frm) {
	const preview = frm.__milestone_preview;
	if (!preview || !preview.to_update.length) return;

	const checked_idxs = [];
	frm.fields_dict.import_preview.$wrapper.find(".milestone-import-check:checked").each(function () {
		checked_idxs.push(parseInt($(this).attr("data-idx"), 10));
	});
	const selected = checked_idxs.map((i) => preview.to_update[i]);
	if (!selected.length) {
		frappe.msgprint(__("Select at least one milestone to update."));
		return;
	}

	frappe.call({
		doc: frm.doc,
		method: "apply_import",
		args: { updates: selected },
		freeze: true,
		freeze_message: __("Updating milestones..."),
		callback(r) {
			if (!r.message) return;
			frm.__milestone_preview = null;
			frappe.show_alert({
				message: __("{0} milestone(s) updated, {1} skipped, {2} failed.", [
					r.message.updated_count,
					r.message.skipped_count,
					r.message.failed_count,
				]),
				indicator: r.message.failed_count ? "orange" : "green",
			});
			frm.reload_doc();
		},
	});
}

function render_preview(frm, result) {
	const { to_update, already_done, unmatched_jobs, milestone_not_enabled, unmapped_columns } = result;
	const esc = frappe.utils.escape_html;
	let html = "";

	if (to_update.length) {
		html += `<h5>${__("Will update")} (${to_update.length})</h5>`;
		html += `<table class="table table-bordered"><thead><tr>
			<th style="width:30px"></th><th>${__("Job")}</th><th>${__("Milestone")}</th><th>${__("Date")}</th>
		</tr></thead><tbody>`;
		to_update.forEach((row, idx) => {
			html += `<tr>
				<td><input type="checkbox" class="milestone-import-check" data-idx="${idx}" checked></td>
				<td>${esc(row.job)}</td>
				<td>${esc(row.milestone_label)}</td>
				<td>${frappe.datetime.str_to_user(row.completed_on)}</td>
			</tr>`;
		});
		html += "</tbody></table>";
	} else {
		html += `<p>${__("No new milestones to update.")}</p>`;
	}

	if (already_done.length) {
		html += `<h5 class="text-muted">${__("Already completed")} (${already_done.length})</h5>`;
		html += `<table class="table table-bordered text-muted"><thead><tr>
			<th>${__("Job")}</th><th>${__("Milestone")}</th><th>${__("Existing Date")}</th>
		</tr></thead><tbody>`;
		already_done.forEach((row) => {
			html += `<tr>
				<td>${esc(row.job)}</td>
				<td>${esc(row.milestone_label)}</td>
				<td>${row.existing_completed_on ? frappe.datetime.str_to_user(row.existing_completed_on) : ""}</td>
			</tr>`;
		});
		html += "</tbody></table>";
	}

	if (unmatched_jobs.length) {
		html += `<h5 class="text-muted">${__("Job references not found")} (${unmatched_jobs.length})</h5>`;
		html += `<p class="text-muted">${unmatched_jobs.map(esc).join(", ")}</p>`;
	}

	if (milestone_not_enabled.length) {
		html += `<h5 class="text-muted">${__("Milestone not applicable")} (${milestone_not_enabled.length})</h5>`;
		html += `<p class="text-muted">${milestone_not_enabled
			.map((r) => esc(`${r.job}: ${r.milestone_label}`))
			.join("; ")}</p>`;
	}

	if (unmapped_columns.length) {
		html += `<h5 class="text-muted">${__("Unmapped columns (ignored)")}</h5>`;
		html += `<p class="text-muted">${unmapped_columns.map(esc).join(", ")}</p>`;
	}

	frm.fields_dict.import_preview.$wrapper.html(html);
}

function render_results_summary(frm) {
	const html = `<p>${__("Updated")}: ${frm.doc.updated_count || 0}, ${__("Skipped")}: ${
		frm.doc.skipped_count || 0
	}, ${__("Failed")}: ${frm.doc.failed_count || 0}</p>`;
	frm.fields_dict.import_preview.$wrapper.html(html);
}
