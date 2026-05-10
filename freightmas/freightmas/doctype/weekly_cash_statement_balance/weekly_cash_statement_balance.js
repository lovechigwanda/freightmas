frappe.ui.form.on('Weekly Cash Statement Balance', {
	refresh(frm) {
		frm.set_query('account', 'balances', () => ({
			filters: {
				account_type: ['in', ['Cash', 'Bank']]
			}
		}));
	}
});
