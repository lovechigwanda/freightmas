// Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Fuel Order", {
// 	refresh(frm) {

// 	},
// });


/////////////////////////////////////////////////////////////////////////////////

// ACTUAL LITRES only editable at the correct stage (after approval)

frappe.ui.form.on('Fuel Order', {
    validate: function(frm) {
        if (frm.doc.status !== "Approved" && frm.doc.actual_litres) {
            frappe.throw("Actual Litres can only be entered after approval.");
        }
    }
});

///Make actual_litres Required before completion

//frappe.ui.form.on("Fuel Order", {
    //validate: function(frm) {
        //if (frm.doc.status === "Completed" && (!frm.doc.actual_litres || frm.doc.actual_litres <= 0)) {
            //frappe.throw("You must enter Actual Litres before marking the Fuel Order as Completed.");
       // }
    //}
//});



//////////////////////////////////////////////////////////////////////////////////////

frappe.ui.form.on('Fuel Order', {
    refresh: function (frm) {
        // Show buttons only when the document is approved
        if (frm.doc.status === "Approved") {
            frm.add_custom_button('WA Direct', () => {
                send_to_whatsapp_direct(frm);
            }, 'Create'); // Attach to the "Create" dropdown

            frm.add_custom_button('WA Copy Text', () => {
                show_copy_text_dialog(frm);
            }, 'Create'); // Attach to the "Create" dropdown
        }
    },
});

// Function for sending message to WhatsApp directly
function send_to_whatsapp_direct(frm) {
    if (!frm.doc.supplier_whatsapp_number) {
        frappe.msgprint("Supplier WhatsApp Number is not available. Please add it before sending the message.");
        return;
    }

    // Prepare the WhatsApp message
    const message = prepare_whatsapp_message(frm);

    // Generate the WhatsApp URL
    const whatsapp_url = `https://api.whatsapp.com/send?phone=${frm.doc.supplier_whatsapp_number}&text=${encodeURIComponent(message)}`;

    // Open WhatsApp Web with the pre-filled message
    window.open(whatsapp_url, "_blank");
}

// Function for showing dialog with formatted WhatsApp message for copy
function show_copy_text_dialog(frm) {
    const message = prepare_whatsapp_message(frm);

    // Create a dialog box for copying the message
    const dialog = new frappe.ui.Dialog({
        title: "Copy WhatsApp Message",
        fields: [
            {
                fieldname: "whatsapp_message",
                fieldtype: "Text",
                label: "WhatsApp Message",
                default: message,
                read_only: 1,
            },
        ],
        primary_action_label: "Copy",
        primary_action(values) {
            copy_to_clipboard(message);
            frappe.show_alert({ message: "Message copied to clipboard", indicator: "green" });
            dialog.hide();
        },
    });

    dialog.show();
}

// Function to copy text to the clipboard with fallback
function copy_to_clipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text)
            .then(() => {
                frappe.show_alert({ message: "Message copied to clipboard", indicator: "green" });
            })
            .catch((err) => {
                frappe.msgprint("Failed to copy message. Please copy manually.");
                console.error("Clipboard copy failed:", err);
            });
    } else {
        // Fallback to the textarea method
        const textarea = document.createElement("textarea");
        textarea.value = text;

        // Prevent scrolling to the bottom
        textarea.style.position = "fixed";
        textarea.style.top = "0";
        textarea.style.left = "0";
        textarea.style.opacity = "0";

        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {
            const successful = document.execCommand("copy");
            if (!successful) {
                throw new Error("Copy command failed");
            }
            frappe.show_alert({ message: "Message copied to clipboard", indicator: "green" });
        } catch (err) {
            frappe.msgprint("Unable to copy message. Please copy manually.");
        }

        document.body.removeChild(textarea);
    }
}

// Function to prepare the WhatsApp message
function prepare_whatsapp_message(frm) {
    return `
        *Fuel Order Details:*
        - Company: ${frappe.boot.sysdefaults.company || "N/A"}
        - Order No: ${frm.doc.name || "N/A"}
        - Order Date: ${frm.doc.order_date || "N/A"}
        - Truck: ${frm.doc.truck || "N/A"}
        - Driver: ${frm.doc.driver || "N/A"}
        - Passport No: ${frm.doc.passport_number || "N/A"}
        - Cell No: ${frm.doc.cell_number || "N/A"}
        - Cell No 2: ${frm.doc.cell_number2 || "N/A"}
        - Fueling At: ${frm.doc.fuel_location || "N/A"}
        - Litres: *${frm.doc.required_litres || "N/A"}*
    `;
}



/////////////////////////////////////////////////////////////////////


//////////////////CREATE PURCHASE INVOICE

frappe.ui.form.on("Fuel Order", {
    refresh: function (frm) {
        // Show the "Purchase Receipt" button only if the Fuel Order is Completed and no existing receipt
        if (frm.doc.status === "Completed" && !frm.doc.purchase_receipt) {
            frm.add_custom_button("Purchase Receipt", function () {
                frappe.call({
                    method: "freightmas.trucking_service.doctype.fuel_order.fuel_order.create_purchase_receipt",
                    args: {
                        fuel_order: frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.show_alert({
                                message: `Purchase Receipt <b>${r.message}</b> created.`,
                                indicator: "green"
                            });
                            frm.reload_doc();
                            frappe.set_route("Form", "Purchase Receipt", r.message);
                        }
                    }
                });
            }, "Create");
        }
    }
});



///////////////////////////////////////////////
