// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cash Reconciliation", {
	setup(frm) {
		frm.set_query("cash_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					account_type: "Cash",
					is_group: 0,
				},
			};
		});
	},

	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Ledger Balance"), function () {
				frm.trigger("fetch_ledger_balance");
			});

			// Prevent submit if difference exists but no remarks
			if (flt(frm.doc.difference, 2) !== 0 && !frm.doc.remarks) {
				frm.page.btn_secondary.find(".primary-action").prop("disabled", true);
				frappe.msgprint(__("(!) Remarks are required before submitting a reconciliation with a cash difference."));
			}
		}
	},

	company(frm) {
		frm.set_value("cash_account", "");
	},

	posting_date(frm) {
		// Warn user that ledger balance is now stale if it was previously fetched
		if (frm.doc.fetched_on) {
			frappe.msgprint(__("Posting Date has changed. Please click 'Fetch Ledger Balance' to refresh."));
			frm.set_value("ledger_balance", null);
			frm.set_value("fetched_on", null);
			frm.trigger("calculate_difference");
		}
		frm.set_value("period_from", null);
		frm.set_value("period_to", null);
		frm.set_value("period_receipts", null);
		frm.set_value("period_payments", null);
		frm.set_value("period_net_flow", null);
		frm.trigger("fetch_period_flow");
	},

	period_type(frm) {
		frm.trigger("fetch_period_flow");
	},

	physical_cash_balance(frm) {
		frm.trigger("calculate_difference");
	},

	ledger_balance(frm) {
		frm.trigger("calculate_difference");
	},

	fetch_ledger_balance(frm) {
		if (!frm.doc.company || !frm.doc.cash_account || !frm.doc.posting_date) {
			frappe.msgprint(__("Please select Company, Cash Account, and Posting Date first."));
			return;
		}

		frappe.call({
			method: "freightmas.freightmas.doctype.cash_reconciliation.cash_reconciliation.get_cash_ledger_balance",
			args: {
				company: frm.doc.company,
				cash_account: frm.doc.cash_account,
				posting_date: frm.doc.posting_date,
			},
			callback: function (r) {
				if (r.message !== undefined) {
					frm.set_value("ledger_balance", r.message);
					frm.set_value("fetched_on", frappe.datetime.now_datetime());
					frm.trigger("calculate_difference");
					frm.trigger("fetch_period_flow");
				}
			},
		});
	},

	fetch_period_flow(frm) {
		if (!frm.doc.company || !frm.doc.cash_account || !frm.doc.posting_date) return;
		frappe.call({
			method: "freightmas.freightmas.doctype.cash_reconciliation.cash_reconciliation.get_period_flow",
			args: {
				company: frm.doc.company,
				cash_account: frm.doc.cash_account,
				posting_date: frm.doc.posting_date,
				period_type: frm.doc.period_type || "Day",
			},
			callback(r) {
				if (r.message) {
					frm.set_value("period_from", r.message.period_from);
					frm.set_value("period_to", r.message.period_to);
					frm.set_value("period_receipts", r.message.period_receipts);
					frm.set_value("period_payments", r.message.period_payments);
					frm.set_value("period_net_flow", r.message.period_net_flow);
				}
			},
		});
	},

	remarks(frm) {
		// Re-enable submit button if remarks now filled and difference exists
		if (flt(frm.doc.difference, 2) !== 0 && frm.doc.remarks) {
			frm.page.btn_secondary.find(".primary-action").prop("disabled", false);
		}
	},

	calculate_difference(frm) {
		let physical = flt(frm.doc.physical_cash_balance);
		let ledger = flt(frm.doc.ledger_balance);
		let difference = physical - ledger;
		frm.set_value("difference", difference);
		frm.set_value("reconciliation_status", flt(difference, 2) === 0 ? "Balanced" : "Difference");

		// Update submit button state based on remarks requirement
		if (flt(difference, 2) !== 0 && !frm.doc.remarks) {
			frm.page.btn_secondary.find(".primary-action").prop("disabled", true);
		} else if (flt(difference, 2) !== 0 && frm.doc.remarks) {
			frm.page.btn_secondary.find(".primary-action").prop("disabled", false);
		}
	},
});
