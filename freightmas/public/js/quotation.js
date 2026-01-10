frappe.ui.form.on('Quotation', {
    items_on_form_rendered(frm) {
        calculate_totals(frm);
    },
    items_add(frm) {
        calculate_totals(frm);
    },
    items_remove(frm) {
        calculate_totals(frm);
    },
    refresh(frm) {
        calculate_totals(frm);

        // Only show the button if the document is saved (not new)
        if (!frm.is_new()) {
            frm.add_custom_button('View Cost Sheet', function() {
                window.open(
                    `/printview?doctype=Quotation&name=${frm.doc.name}&format=Quotation%20Cost%20Sheet&no_letterhead=1`,
                    '_blank'
                );
            });
            
            // Add "Create Job Order" button for Accepted Forwarding quotations
            if (frm.doc.workflow_state === 'Accepted' && frm.doc.job_type === 'Forwarding') {
                // Check if job order already exists
                frappe.db.get_value('Job Order', 
                    {'quotation_reference': frm.doc.name, 'docstatus': ['<', 2]}, 
                    'name',
                    (r) => {
                        if (r && r.name) {
                            // Job Order exists - add button to view it
                            frm.add_custom_button(__('View Job Order'), function() {
                                frappe.set_route('Form', 'Job Order', r.name);
                            }, __('View'));
                            
                            frm.dashboard.add_comment(
                                __('Job Order {0} has been created from this Quotation', [r.name]),
                                'blue',
                                true
                            );
                        } else {
                            // No Job Order exists - add button to create it
                            frm.add_custom_button(__('Create Job Order'), function() {
                                create_job_order_from_quotation(frm);
                            }, __('Create')).addClass('btn-primary');
                        }
                    }
                );
            }
        }
    },
    validate(frm) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let est_revenue = 0;
    let est_cost = 0;

    (frm.doc.items || []).forEach(item => {
        est_revenue += flt(item.amount);
        est_cost += flt(item.cost_amount);
    });

    frm.set_value('est_revenue', est_revenue);
    frm.set_value('est_cost', est_cost);
    frm.set_value('est_profit', est_revenue - est_cost);
}

frappe.ui.form.on('Quotation Item', {
    qty(frm, cdt, cdn) {
        update_cost_amount(frm, cdt, cdn);
    },
    buy_rate(frm, cdt, cdn) {
        update_cost_amount(frm, cdt, cdn);
    }
});

function update_cost_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "cost_amount", (row.qty || 0) * (row.buy_rate || 0));
    calculate_totals(frm);
}

// ===================================
// Job Order Creation
// ===================================

function create_job_order_from_quotation(frm) {
    frappe.confirm(
        __('Create a Job Order from this Quotation?<br><br>This will:<br>- Create a new Job Order document<br>- Copy all service charges<br>- Link the Job Order to this Quotation<br><br>The Job Order will be the official handover from Sales to Operations.'),
        function() {
            // User confirmed
            frappe.call({
                method: 'freightmas.freightmas.job_order_integration.create_job_order_from_quotation',
                args: {
                    quotation_name: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Creating Job Order...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Job Order {0} created successfully!', [r.message]),
                            indicator: 'green'
                        }, 5);
                        
                        frm.reload_doc();
                        
                        // Offer to open the new Job Order
                        setTimeout(function() {
                            frappe.confirm(
                                __('Would you like to open the newly created Job Order?'),
                                function() {
                                    frappe.set_route('Form', 'Job Order', r.message);
                                }
                            );
                        }, 1000);
                    }
                }
            });
        }
    );
}
