const INVOICING_INSTRUCTION_STATUS = {
    'Draft': ['Draft', 'red'],
    'Submitted': ['Ready for Action', 'blue'],
    'Actioned': ['Actioned', 'green'],
    'Cancelled': ['Cancelled', 'grey']
};

frappe.listview_settings['Invoicing Instruction'] = {
    add_fields: [
        'status',
        'forwarding_job',
        'customer',
        'total_amount',
        'currency',
        'total_items',
        'requested_by',
        'requested_on',
        'linked_register_entry',
        'linked_sales_invoice'
    ],

    get_indicator(doc) {
        const status = INVOICING_INSTRUCTION_STATUS[doc.status] || [doc.status || 'Unknown', 'grey'];
        return [__(status[0]), status[1], 'status,=,' + doc.status];
    },

    onload(listview) {
        add_invoicing_instruction_queue_buttons(listview);
    },

    formatters: {
        status(value) {
            return value ? frappe.utils.escape_html(value) : '';
        },

        forwarding_job(value) {
            return value ? `<span style="font-weight:600;">${frappe.utils.escape_html(value)}</span>` : '';
        },

        total_amount(value, df, doc) {
            if (!value) return '';
            return `<strong>${frappe.format(value, { fieldtype: 'Currency', currency: doc.currency })}</strong>`;
        },

        total_items(value) {
            if (!value) return '';
            return `<span style="background:#f3f4f6;border-radius:12px;padding:2px 8px;font-size:12px;">${value} ${__('item(s)')}</span>`;
        },

        linked_register_entry(value) {
            if (!value) return '';
            return `<span style="color:#15803d;font-weight:600;">${frappe.utils.escape_html(value)}</span>`;
        },

        linked_sales_invoice(value) {
            if (!value) return '';
            return `<span style="color:#15803d;font-weight:600;">${frappe.utils.escape_html(value)}</span>`;
        }
    }
};

function add_invoicing_instruction_queue_buttons(listview) {
    const open_queue = (label, filters) => {
        listview.page.add_inner_button(__(label), function () {
            frappe.route_options = filters;
            frappe.set_route('List', 'Invoicing Instruction');
        }, __('Queues'));
    };

    open_queue('Needs Action', {
        status: ['in', ['Draft', 'Submitted']]
    });

    open_queue('Ready for Action', {
        status: 'Submitted'
    });

    open_queue('Actioned', {
        status: 'Actioned'
    });
}
