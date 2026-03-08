/* FreightMas Management Accounts Export
 * Dialog for exporting comprehensive Management Accounts as a multi-sheet Excel file.
 */

frappe.provide("freightmas.management_accounts");

// Attach export button to FreightMas Accounts workspace when it loads
document.addEventListener("DOMContentLoaded", function () {
	frappe.router.on("change", function () {
		if (
			frappe.get_route_str() === "Workspaces/FreightMas Accounts" ||
			frappe.get_route_str() === "workspaces/FreightMas Accounts"
		) {
			// Small delay to let workspace render
			setTimeout(function () {
				add_export_button_to_workspace();
			}, 500);
		}
	});
});

function add_export_button_to_workspace() {
	// Avoid duplicate buttons
	if (document.querySelector(".management-accounts-export-btn")) return;

	let page = cur_page && cur_page.page;
	if (page && page.add_inner_button) {
		page.add_inner_button(
			__("Export Management Accounts"),
			function () {
				freightmas.management_accounts.show_export_dialog();
			},
			null,
			"primary"
		);
		// Tag the button so we don't add duplicates
		let btn = page.inner_toolbar.find('button:contains("Export Management Accounts")');
		if (btn.length) {
			btn.addClass("management-accounts-export-btn");
		}
	}
}

freightmas.management_accounts.show_export_dialog = function () {
	const default_company = frappe.defaults.get_user_default("Company");

	let d = new frappe.ui.Dialog({
		title: __("Export Management Accounts"),
		size: "large",
		fields: [
			{
				fieldname: "company",
				label: __("Company"),
				fieldtype: "Link",
				options: "Company",
				reqd: 1,
				default: default_company,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "filter_based_on",
				label: __("Filter Based On"),
				fieldtype: "Select",
				options: ["Fiscal Year", "Date Range"],
				reqd: 1,
				default: "Fiscal Year",
				change: function () {
					toggle_date_fields(d);
				},
			},
			{ fieldtype: "Section Break", label: __("Period") },
			{
				fieldname: "from_fiscal_year",
				label: __("From Fiscal Year"),
				fieldtype: "Link",
				options: "Fiscal Year",
				reqd: 1,
				default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
				depends_on: 'eval:doc.filter_based_on=="Fiscal Year"',
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "to_fiscal_year",
				label: __("To Fiscal Year"),
				fieldtype: "Link",
				options: "Fiscal Year",
				reqd: 1,
				default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
				depends_on: 'eval:doc.filter_based_on=="Fiscal Year"',
			},
			{ fieldtype: "Section Break", label: __("Date Range"), depends_on: 'eval:doc.filter_based_on=="Date Range"' },
			{
				fieldname: "from_date",
				label: __("From Date"),
				fieldtype: "Date",
				reqd: 1,
				default: frappe.datetime.year_start(),
				depends_on: 'eval:doc.filter_based_on=="Date Range"',
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "to_date",
				label: __("To Date"),
				fieldtype: "Date",
				reqd: 1,
				default: frappe.datetime.get_today(),
				depends_on: 'eval:doc.filter_based_on=="Date Range"',
			},
			{ fieldtype: "Section Break", label: __("Options") },
			{
				fieldname: "periodicity",
				label: __("Periodicity"),
				fieldtype: "Select",
				options: ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
				default: "Yearly",
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "presentation_currency",
				label: __("Currency"),
				fieldtype: "Link",
				options: "Currency",
			},
			{ fieldtype: "Section Break", label: __("Filters") },
			{
				fieldname: "cost_center",
				label: __("Cost Center"),
				fieldtype: "MultiSelectList",
				get_data: function (txt) {
					let company = d.get_value("company");
					return frappe.db.get_link_options("Cost Center", txt, {
						company: company,
					});
				},
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "finance_book",
				label: __("Finance Book"),
				fieldtype: "Link",
				options: "Finance Book",
			},
			{
				fieldtype: "Section Break",
			},
			{
				fieldname: "reports_info",
				fieldtype: "HTML",
				options: get_reports_info_html(),
			},
		],
		primary_action_label: __("Export"),
		primary_action: function () {
			let values = d.get_values();
			if (!values) return;

			// Validate
			if (values.filter_based_on === "Fiscal Year") {
				if (!values.from_fiscal_year || !values.to_fiscal_year) {
					frappe.msgprint(__("Please select Fiscal Year range."));
					return;
				}
			} else {
				if (!values.from_date || !values.to_date) {
					frappe.msgprint(__("Please select Date Range."));
					return;
				}
				if (values.from_date > values.to_date) {
					frappe.msgprint(__("From Date cannot be after To Date."));
					return;
				}
			}

			// Handle MultiSelectList value (returns array of objects)
			if (values.cost_center && Array.isArray(values.cost_center)) {
				values.cost_center = values.cost_center.map((v) =>
					typeof v === "object" ? v.value : v
				);
			}

			frappe.show_alert({
				message: __("Generating Management Accounts... This may take a moment."),
				indicator: "blue",
			});

			let url =
				"/api/method/freightmas.api.export_management_accounts?filters=" +
				encodeURIComponent(JSON.stringify(values));
			window.open(url);
			d.hide();
		},
	});

	d.show();
};

function toggle_date_fields(d) {
	d.refresh();
}

function get_reports_info_html() {
	return `
		<div style="background:#f5f7fa; border-radius:6px; padding:12px 16px; margin-top:4px;">
			<div style="font-weight:600; margin-bottom:8px; color:#333;">
				Reports included in this export:
			</div>
			<div style="display:grid; grid-template-columns:1fr 1fr; gap:4px 24px; font-size:12px; color:#555;">
				<div>1. Profit &amp; Loss Statement</div>
				<div>8. Revenue Detail</div>
				<div>2. P&amp;L by Cost Center</div>
				<div>9. Direct Expenses Detail</div>
				<div>3. Balance Sheet</div>
				<div>10. Indirect Expenses Detail</div>
				<div>4. Cash Flow Statement</div>
				<div>11. Cash &amp; Bank Balance</div>
				<div>5. Trial Balance</div>
				<div>12. Debtors Listing</div>
				<div>6. Budget Variance</div>
				<div>13. Creditors Listing</div>
				<div>7. Asset Register</div>
				<div></div>
			</div>
		</div>
	`;
}
