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
    // Trigger calculation when quantity or rate is changed
    quantity: function(frm, cdt, cdn) {
        calculate_revenue_total(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_revenue_total(frm, cdt, cdn);
    },
    revenue_charges_remove: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Trip Fuel Costs', {
    // Trigger calculation when quantity or rate is changed
    quantity: function(frm, cdt, cdn) {
        calculate_fuel_cost_total(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_fuel_cost_total(frm, cdt, cdn);
    },
    trip_fuel_costs_remove: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Trip Other Costs', {
    // Trigger calculation when quantity or rate is changed
    quantity: function(frm, cdt, cdn) {
        calculate_other_cost_total(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_other_cost_total(frm, cdt, cdn);
    },
    trip_other_costs_remove: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Trip Commissions', {
    // Trigger calculation when quantity or rate is changed
    quantity: function(frm, cdt, cdn) {
        calculate_commission_total(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_commission_total(frm, cdt, cdn);
    },
    trip_commissions_remove: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_revenue_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total_amount = row.quantity * row.rate;
    frm.refresh_field('trip_revenue_charges');
    calculate_totals(frm);
}

function calculate_fuel_cost_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total_amount = row.quantity * row.rate;
    frm.refresh_field('trip_fuel_costs');
    calculate_totals(frm);
}

function calculate_other_cost_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total_amount = row.quantity * row.rate;
    frm.refresh_field('trip_other_costs');
    calculate_totals(frm);
}

function calculate_commission_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total_amount = row.quantity * row.rate;
    frm.refresh_field('trip_commissions');
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_revenue = 0;
    let total_fuel_cost = 0;
    let total_other_costs = 0;
    let total_commissions = 0;

    // Sum up revenue charges
    frm.doc.trip_revenue_charges.forEach(function(d) {
        total_revenue += d.total_amount;
    });

    // Sum up fuel costs
    frm.doc.trip_fuel_costs.forEach(function(d) {
        total_fuel_cost += d.total_amount;
    });

    // Sum up other costs
    frm.doc.trip_other_costs.forEach(function(d) {
        total_other_costs += d.total_amount;
    });

    // Sum up commissions
    frm.doc.trip_commissions.forEach(function(d) {
        total_commissions += d.total_amount;
    });

    // Set total fields and calculate profit
    frm.set_value('total_estimated_revenue', total_revenue);
    frm.set_value('total_estimated_cost', total_fuel_cost + total_other_costs + total_commissions);
    frm.set_value('estimated_profit', total_revenue - (total_fuel_cost + total_other_costs + total_commissions));
}


////////////////////////////////////////////////////////////////////////////////////////////////////

///////////////////////////////////////////////////////////////////////////////////////////////////

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


////CREATE PURCHASE INVOICE FROM TRIP COST CHARGES
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

//CREATE STOCK ENTRY FROM FUEL COSTS CHARGES

frappe.ui.form.on('Trip', {
    refresh: function (frm) {
        // Add the "Stock Entry" button under the "Create" dropdown
        frm.add_custom_button('Stock Entry', () => {
            let dialog = new frappe.ui.Dialog({
                title: 'Create Stock Entry',
                fields: [
                    {
                        fieldtype: 'Link',
                        fieldname: 'warehouse',
                        options: 'Warehouse',
                        label: 'Source Warehouse',
                        reqd: 1,
                        onchange: function () {
                            const warehouse = dialog.get_value('warehouse');
                            const costs = frm.doc.trip_fuel_costs.filter(c => {
                                return !c.is_invoiced && c.warehouse === warehouse;
                            });
                            dialog.fields_dict.costs.df.data = costs;
                            dialog.fields_dict.costs.refresh();
                        },
                    },
                    {
                        fieldtype: 'Table',
                        fieldname: 'costs',
                        label: 'Select Fuel Costs',
                        fields: [
                            {
                                fieldtype: 'Data',
                                fieldname: 'name',
                                label: 'ID',
                                hidden: 1,
                            },
                            {
                                fieldtype: 'Link',
                                fieldname: 'item_code',
                                label: 'Fuel Item',
                                options: 'Item',
                                in_list_view: 1,
                            },
                            {
                                fieldtype: 'Float',
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
                            {
                                fieldtype: 'Float',
                                fieldname: 'total_amount', // Updated field name
                                label: 'Total Amount',
                                in_list_view: 1,
                                read_only: 1,
                            },
                        ],
                        data: [],
                        get_data: function () {
                            const warehouse = dialog.get_value('warehouse');
                            return frm.doc.trip_fuel_costs.filter(c => {
                                return !c.is_invoiced && c.warehouse === warehouse;
                            });
                        },
                    },
                ],
                primary_action_label: 'Create Stock Entry',
                primary_action: function () {
                    const values = dialog.get_values();

                    if (!values || !values.warehouse || !values.costs || values.costs.length === 0) {
                        frappe.msgprint('Please select a warehouse and at least one fuel cost.');
                        return;
                    }

                    const selected_costs = values.costs.map(c => c.name);

                    frappe.call({
                        method: 'freightmas.trucking_service.doctype.trip.trip.create_stock_entry_from_fuel_costs',
                        args: {
                            trip_name: frm.doc.name,
                            selected_costs,
                            source_warehouse: values.warehouse,
                        },
                        callback: function (response) {
                            if (response.message) {
                                frappe.msgprint(`Stock Entry Created: ${response.message.stock_entry_name}`);
                                frappe.set_route('Form', 'Stock Entry', response.message.stock_entry_name);
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

// PREVENT DELETION OF INVOICED FUEL COSTS

frappe.ui.form.on('Trip Fuel Costs', {
    before_trip_fuel_costs_remove: function (frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.is_invoiced) {
            frappe.throw(__("You cannot delete an invoiced fuel cost."));
        }
    }
});

/////////////////////////////////////////////////////////////////////////////////////



///////////////////////////////////////////////////////////////////////
