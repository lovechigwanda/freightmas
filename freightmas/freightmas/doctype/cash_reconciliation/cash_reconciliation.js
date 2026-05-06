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
		}
	},

	company(frm) {
		frm.set_value("cash_account", "");
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
				}
			},
		});
	},

	calculate_difference(frm) {
		let physical = flt(frm.doc.physical_cash_balance);
		let ledger = flt(frm.doc.ledger_balance);
		let difference = physical - ledger;
		frm.set_value("difference", difference);
		frm.set_value("reconciliation_status", flt(difference, 2) === 0 ? "Balanced" : "Difference");
	},
});
