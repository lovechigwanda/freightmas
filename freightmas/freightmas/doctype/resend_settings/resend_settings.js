// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Resend Settings", {
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

		frm.add_custom_button(__("Send Test Email"), () => {
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
		});
	},
});
