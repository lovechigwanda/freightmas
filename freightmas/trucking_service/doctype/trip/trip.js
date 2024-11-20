// Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Trip", {
// 	refresh(frm) {

// 	},
// });

///////////////////////////////////////////////////////////////////////////////////////////////

// CALCULATE PROFIT IN TRIP DOCTYPE
frappe.ui.form.on('Trip', {
    // Trigger calculations when the form is refreshed or validated
    refresh: function(frm) {
        calculate_totals(frm);
    },
    validate: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Trip Revenue Charges', {
    // Trigger calculation when quantity is changed
    quantity: function(frm, cdt, cdn) {
        calculate_revenue_total(frm, cdt, cdn);
    },
    // Trigger calculation when rate is changed
    rate: function(frm, cdt, cdn) {
        calculate_revenue_total(frm, cdt, cdn);
    },
    // Recalculate totals when a row is removed from Revenue Charges
    revenue_charges_remove: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Trip Cost Charges', {
    // Trigger calculation when quantity is changed
    quantity: function(frm, cdt, cdn) {
        calculate_cost_total(frm, cdt, cdn);
    },
    // Trigger calculation when rate is changed
    rate: function(frm, cdt, cdn) {
        calculate_cost_total(frm, cdt, cdn);
    },
    // Recalculate totals when a row is removed from Cost Charges
    cost_charges_remove: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_revenue_total(frm, cdt, cdn) {
    // Get the current row in Revenue Charges
    let row = locals[cdt][cdn];
    // Calculate the total amount for the current row
    row.total_amount = row.quantity * row.rate;
    // Refresh the Revenue Charges table to reflect the changes
    frm.refresh_field('trip_revenue_charges');
    // Recalculate the overall totals
    calculate_totals(frm);
}

function calculate_cost_total(frm, cdt, cdn) {
    // Get the current row in Cost Charges
    let row = locals[cdt][cdn];
    // Calculate the total amount for the current row
    row.total_amount = row.quantity * row.rate;
    // Refresh the Cost Charges table to reflect the changes
    frm.refresh_field('trip_cost_charges');
    // Recalculate the overall totals
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_revenue = 0;
    let total_cost = 0;
    // Sum up all total_amount fields in Revenue Charges
    frm.doc.trip_revenue_charges.forEach(function(d) {
        total_revenue += d.total_amount;
    });
    // Sum up all total_amount fields in Cost Charges
    frm.doc.trip_cost_charges.forEach(function(d) {
        total_cost += d.total_amount;
    });
    // Set the total_estimated_revenue field
    frm.set_value('total_estimated_revenue', total_revenue);
    // Set the total_estimated_cost field
    frm.set_value('total_estimated_cost', total_cost);
    // Calculate and set the estimated_profit field
    frm.set_value('estimated_profit', total_revenue - total_cost);
}


////////////////////////////////////////////////////////////////////////////////////////////////////


//UPDATE CURRENT MILESTONE

frappe.ui.form.on('Trip', {
    before_save: function(frm) {
        var lastRow = frm.doc.trip_tracking_update.slice(-1)[0];

        if (lastRow) {
            // Get the value from the last row's trip_milestone field
            var lastValue = lastRow.trip_milestone;
            var lastValue1 = lastRow.trip_milestone_comment;
            var lastValue2 = lastRow.trip_milestone_date;

            // Set the value in the parent doctype's current_trip_milestone field
            frm.set_value('current_trip_milestone', lastValue);
            frm.set_value('current_milestone_comment', lastValue1);
            frm.set_value('updated_on', lastValue2);
            frm.refresh();
        }
    }
});


/////////////////////////////////////////////////////////////////////////////////////////////////

//FILTER ROUTES BASED ON DIRECTION SELECTED AND ONLY SHOW ACTIVE ROUTES


frappe.ui.form.on('Trip', {
    setup: function(frm) {
        frm.set_query('route', function() {
            if (frm.doc.trip_direction) {
                return {
                    filters: {
                        'trip_direction': frm.doc.trip_direction,
                        'is_deactivated': 0  // Only show routes that are active
                    }
                };
            } else {
                return {
                    filters: {
                        'is_deactivated': 0  // Only show active routes if trip_direction is not set
                    }
                };
            }
        });
    }
});


/////////////////////////////////////////////////////////////////////////////////////////////////



//////////////////////////////////////////////////////////////////////////////

//CREATE SALES INVOICE FROM TRIP REVENUE CHARGES

frappe.ui.form.on('Trip', {
    refresh: function (frm) {
        // Add the "Invoice" button under the "Create" dropdown
        frm.add_custom_button('Sales Invoice', () => {
            let dialog = new frappe.ui.Dialog({
                title: 'Create Sales Invoice',
                fields: [
                    {
                        fieldtype: 'Link',
                        fieldname: 'receivable_party',
                        options: 'Customer',
                        label: 'Receivable Party',
                        reqd: 1,
                        onchange: function () {
                            // Filter charges based on the selected receivable party
                            const receivable_party = dialog.get_value('receivable_party');
                            const charges = frm.doc.trip_revenue_charges.filter(c => {
                                return !c.is_invoiced && c.receivable_party === receivable_party;
                            });
                            dialog.fields_dict.charges.df.data = charges;
                            dialog.fields_dict.charges.refresh();
                        },
                    },
                    {
                        fieldtype: 'Table',
                        fieldname: 'charges',
                        label: 'Select Charges',
                        fields: [
                            {
                                fieldtype: 'Data',
                                fieldname: 'name',
                                label: 'ID',
                                hidden: 1, // Hidden field to pass the charge ID to the server
                            },
                            {
                                fieldtype: 'Data',
                                fieldname: 'charge',
                                label: 'Charge',
                                in_list_view: 1,
                            },
                            {
                                fieldtype: 'Data',
                                fieldname: 'charge_description',
                                label: 'Description',
                                in_list_view: 1,
                            },
                            {
                                fieldtype: 'Int',
                                fieldname: 'quantity',
                                label: 'Quantity',
                                in_list_view: 1,
                            },
                            {
                                fieldtype: 'Float',
                                fieldname: 'rate',
                                label: 'Rate',
                                in_list_view: 1,
                            },
                        ],
                        data: [], // Initially empty, populated dynamically
                        get_data: function () {
                            const receivable_party = dialog.get_value('receivable_party');
                            return frm.doc.trip_revenue_charges.filter(c => {
                                return !c.is_invoiced && c.receivable_party === receivable_party;
                            });
                        },
                    },
                ],
                primary_action_label: 'Create Invoice',
                primary_action: function () {
                    const values = dialog.get_values();

                    // Validate user input
                    if (!values || !values.receivable_party || !values.charges || values.charges.length === 0) {
                        frappe.msgprint('Please select a receivable party and at least one charge to invoice.');
                        return;
                    }

                    // Collect selected charges
                    const selected_charges = values.charges.map(c => c.name);

                    frappe.call({
                        method: 'freightmas.trucking_service.doctype.trip.trip.create_sales_invoice',
                        args: {
                            trip_name: frm.doc.name,
                            selected_charges,
                            receivable_party: values.receivable_party,
                        },
                        callback: function (response) {
                            if (response.message) {
                                // Show success message
                                frappe.msgprint(`Invoice Created: ${response.message.invoice_name}`);

                                // Redirect to the newly created invoice
                                frappe.set_route('Form', 'Sales Invoice', response.message.invoice_name);

                                // Reload the Trip form to reflect changes
                                frm.reload_doc();
                            }
                        },
                    });
                    dialog.hide();
                },
            });

            dialog.show();
        }, 'Create'); // Attach to the "Create" dropdown
    },
});



//////////////////////////////////////////////////////////////////////////


//PREVENT DELETION OF INVOICED REVENUE CHARGES



// Prevent deletion of invoiced rows in the grid
frappe.ui.form.on('Trip Revenue Charges', {
    before_trip_revenue_charges_remove: function (frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.is_invoiced) {
            frappe.throw(__("You cannot delete an invoiced charge."));
        }
    }
});



/////////////////////////////////////////////////////////////////////////

frappe.ui.form.on('Trip', {
    refresh: function (frm) {
        // Add the "Purchase Invoice" button under the "Create" dropdown
        frm.add_custom_button('Purchase Invoice', () => {
            let dialog = new frappe.ui.Dialog({
                title: 'Create Purchase Invoice',
                fields: [
                    {
                        fieldtype: 'Link',
                        fieldname: 'supplier',
                        options: 'Supplier',
                        label: 'Supplier',
                        reqd: 1,
                        onchange: function () {
                            // Filter charges based on the selected supplier
                            const supplier = dialog.get_value('supplier');
                            const charges = frm.doc.trip_cost_charges.filter(c => {
                                return !c.is_invoiced && c.payable_party === supplier;
                            });

                            console.log("Filtered Charges: ", charges); // Debugging
                            dialog.fields_dict.charges.df.data = charges;
                            dialog.fields_dict.charges.refresh();
                        },
                    },
                    {
                        fieldtype: 'Table',
                        fieldname: 'charges',
                        label: 'Select Charges',
                        fields: [
                            {
                                fieldtype: 'Data',
                                fieldname: 'name',
                                label: 'ID',
                                hidden: 1, // Hidden field to pass the charge ID to the server
                            },
                            {
                                fieldtype: 'Data',
                                fieldname: 'charge',
                                label: 'Charge',
                                in_list_view: 1,
                            },
                            {
                                fieldtype: 'Data',
                                fieldname: 'charge_description',
                                label: 'Description',
                                in_list_view: 1,
                            },
                            {
                                fieldtype: 'Int',
                                fieldname: 'quantity',
                                label: 'Quantity',
                                in_list_view: 1,
                            },
                            {
                                fieldtype: 'Float',
                                fieldname: 'rate',
                                label: 'Rate',
                                in_list_view: 1,
                            },
                        ],
                        data: [], // Initially empty, populated dynamically
                        get_data: function () {
                            const supplier = dialog.get_value('supplier');
                            return frm.doc.trip_cost_charges.filter(c => {
                                return !c.is_invoiced && c.payable_party === supplier;
                            });
                        },
                    },
                ],
                primary_action_label: 'Create Purchase Invoice',
                primary_action: function () {
                    const values = dialog.get_values();

                    // Validate user input
                    if (!values || !values.supplier || !values.charges || values.charges.length === 0) {
                        frappe.msgprint('Please select a supplier and at least one charge to include in the invoice.');
                        return;
                    }

                    // Collect selected charges
                    const selected_charges = values.charges.map(c => c.name);

                    frappe.call({
                        method: 'freightmas.trucking_service.doctype.trip.trip.create_purchase_invoice',
                        args: {
                            trip_name: frm.doc.name,
                            selected_charges,
                            supplier: values.supplier,
                        },
                        callback: function (response) {
                            if (response.message) {
                                frappe.msgprint(`Purchase Invoice Created: <a href="/app/purchase-invoice/${response.message.invoice_name}">${response.message.invoice_name}</a>`);

                                // Redirect to the newly created invoice
                                frappe.set_route('Form', 'Purchase Invoice', response.message.invoice_name);

                                // Reload the Trip form to reflect changes
                                frm.reload_doc();
                            }
                        },
                    });
                    dialog.hide();
                },
            });

            dialog.show();
        }, 'Create'); // Attach to the "Create" dropdown
    },
});

////////////////////////////////////////////////////////////////////////////////

//PREVENT DELETION OF INVOICED COST CHARGES


// Prevent deletion of invoiced rows in the grid
frappe.ui.form.on('Trip Cost Charges', {
    before_trip_cost_charges_remove: function (frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.is_invoiced) {
            frappe.throw(__("You cannot delete an invoiced charge."));
        }
    }
});

////////////////////////////////////////////////////////////////////////////////////

//ADD BUTTON FOR VIEW TRIP COST SHEET

frappe.ui.form.on('Trip', {
    refresh: function (frm) {
        frm.add_custom_button('Trip Cost Sheet', () => {
            // Ensure trip_name is passed correctly
            frappe.set_route('query-report', 'Trip Cost Sheet', { trip_name: frm.doc.name });
        }, 'View'); // Adds the button under the "View" dropdown
    },
});



////////////////////////////////////////////////////////////////////////////////////////////


///Populate the trip_cost_summary child table when the Trip form is refreshed.

frappe.ui.form.on('Trip', {
    refresh: function (frm) {
        // Call the server-side method to populate the Cost Sheet
        frappe.call({
            method: "freightmas.trucking_service.doctype.trip.trip.get_trip_cost_sheet",
            args: {
                trip_name: frm.doc.name,
            },
            callback: function (response) {
                if (response.message) {
                    // Clear existing data
                    frm.clear_table("trip_cost_summary");

                    // Add new rows
                    response.message.forEach(row => {
                        let child = frm.add_child("trip_cost_summary");
                        frappe.model.set_value(child.doctype, child.name, "party", row.party);
                        frappe.model.set_value(child.doctype, child.name, "charge_type", row.charge_type);
                        frappe.model.set_value(child.doctype, child.name, "total_estimated", row.total_estimated);
                        frappe.model.set_value(child.doctype, child.name, "total_invoiced", row.total_invoiced);
                        frappe.model.set_value(child.doctype, child.name, "difference", row.difference);
                    });

                    // Refresh the field to display the data
                    frm.refresh_field("trip_cost_summary");
                }
            },
        });
    },
});

///////////////////////////////////////////////////////