frappe.ui.form.on('DND Storage Rate Card', {
    fetch_container_types_btn: function(frm) {
        if (frm.is_dirty()) {
            frappe.msgprint(__('Please save the rate card before fetching container types.'));
            return;
        }
        frappe.call({
            method: 'freightmas.forwarding_service.doctype.dnd_storage_rate_card.dnd_storage_rate_card.fetch_container_types',
            args: { rate_card_name: frm.doc.name },
            freeze: true,
            freeze_message: __('Fetching container types...'),
            callback: function(r) {
                if (!r.exc && r.message) {
                    frm.reload_doc();
                    const { added, total } = r.message;
                    if (added > 0) {
                        frappe.show_alert({
                            message: __('{0} container type(s) added. {1} total rows. Enter the rates per container type.', [added, total]),
                            indicator: 'green'
                        }, 7);
                    } else {
                        frappe.show_alert({
                            message: __('All container types are already in the table.'),
                            indicator: 'blue'
                        }, 5);
                    }
                }
            }
        });
    }
});
