// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Resend Settings", {
	onload(frm) {
		const field = frm.get_field("resend_api_key");
		if (field && field.$input) {
			field.$input.attr("autocomplete", "new-password");
		}
	},
	refresh(frm) {
		frappe.call({
			method: "freightmas.freightmas.doctype.resend_settings.resend_settings.get_setup_context",
			callback(r) {
				if (!r.message) {
					return;
				}

				const field = frm.get_field("setup_instructions");
				if (field) {
					field.$wrapper.html(r.message.setup_instructions_html);
				}

				if (!frm.doc.fallback_sender && r.message.suggested_fallback_sender) {
					frm.set_value("fallback_sender", r.message.suggested_fallback_sender);
				}

				if (!frm.doc.allowed_domains && r.message.suggested_allowed_domains) {
					frm.set_value("allowed_domains", r.message.suggested_allowed_domains);
				}
			},
		});

		if (!frappe.user.has_role("System Manager") && !frappe.user.has_role("FreightMas Admin")) {
			return;
		}

		frm.add_custom_button(__("Check Resend Domains"), () => {
			frappe.call({
				method: "freightmas.freightmas.doctype.resend_settings.resend_settings.check_resend_domains",
				freeze: true,
				callback(r) {
					const domains = r.message?.domains || [];
					if (!domains.length) {
						frappe.msgprint(__("No domains are linked to this API key in Resend."));
						return;
					}

					const rows = domains
						.map((d) => `<tr><td>${frappe.utils.escape_html(d.name)}</td><td>${frappe.utils.escape_html(d.status)}</td><td>${frappe.utils.escape_html(d.region || "")}</td></tr>`)
						.join("");

					frappe.msgprint({
						title: __("Resend Domains for this API Key"),
						message: `<table class="table table-bordered table-sm"><thead><tr><th>${__("Domain")}</th><th>${__("Status")}</th><th>${__("Region")}</th></tr></thead><tbody>${rows}</tbody></table>`,
						wide: true,
					});
				},
			});
		});

		frm.add_custom_button(__("Send Test Email"), () => {
			const send = () => {
				frappe.call({
					method: "freightmas.freightmas.doctype.resend_settings.resend_settings.send_test_email",
					args: {
						recipient: frm.doc.test_recipient || undefined,
					},
					freeze: true,
					freeze_message: __("Sending test email..."),
					callback(r) {
						if (r.message?.message) {
							frappe.show_alert({ message: r.message.message, indicator: "green" });
						}
					},
				});
			};

			if (frm.is_dirty()) {
				frappe.confirm(
					__("Save Resend Settings first so your API key is stored, then send the test email?"),
					() => frm.save().then(send)
				);
				return;
			}

			send();
		});
	},
});
