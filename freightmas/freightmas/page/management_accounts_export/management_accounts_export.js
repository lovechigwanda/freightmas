frappe.pages["management-accounts-export"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Export Management Accounts"),
		single_column: true,
	});
};

frappe.pages["management-accounts-export"].on_page_show = function () {
	// Automatically open the export dialog when the page loads
	freightmas.management_accounts.show_export_dialog();
};
