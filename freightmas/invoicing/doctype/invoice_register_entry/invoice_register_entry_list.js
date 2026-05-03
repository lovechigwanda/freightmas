const INVOICE_REGISTER_STATUS = {
    'Received': ['New Supplier Invoice', 'blue'],
    'Submitted for Approval': ['Approval Needed', 'orange'],
    'Returned for Capture': ['Capture Correction', 'orange'],
    'Query with Supplier': ['Supplier Query', 'red'],
    'Ready for Capture': ['Ready to Capture', 'blue'],
    'Captured': ['Captured', 'green'],
    'Instruction Received': ['New Instruction', 'blue'],
    'Drafted': ['Drafted', 'orange'],
    'Returned to Draft': ['Returned to Draft', 'orange'],
    'Issued to Client': ['Issued', 'green'],
    'Cancelled': ['Cancelled', 'grey']
};

frappe.listview_settings['Invoice Register Entry'] = {
    add_fields: [
        'status',
        'entry_type',
        'party',
        'job_name',
        'amount',
        'currency',
        'is_overdue',
        'linked_purchase_invoice',
        'linked_sales_invoice',
        'supplier_invoice_no',
        'entry_date'
    ],

    get_indicator(doc) {
        if (doc.is_overdue && !['Captured', 'Issued to Client', 'Cancelled'].includes(doc.status)) {
            return [__('Overdue'), 'red', 'is_overdue,=,1'];
        }

        const status = INVOICE_REGISTER_STATUS[doc.status] || [doc.status || 'Unknown', 'grey'];
        return [__(status[0]), status[1], 'status,=,' + doc.status];
    },

    onload(listview) {
        add_invoice_register_queue_buttons(listview);
    },

    formatters: {
        entry_type(value) {
            if (!value) return '';
            const colour = value === 'Purchase' ? '#fff3cd' : '#dbeafe';
            const text = value === 'Purchase' ? '#8a5a00' : '#1d4ed8';
            return `<span style="background:${colour};color:${text};border-radius:12px;padding:2px 8px;font-size:12px;font-weight:600;">${__(value)}</span>`;
        },

        amount(value, df, doc) {
            if (!value) return '';
            return `<strong>${frappe.format(value, { fieldtype: 'Currency', currency: doc.currency })}</strong>`;
        },

        party(value) {
            return value ? `<span title="${frappe.utils.escape_html(value)}">${frappe.utils.escape_html(value)}</span>` : '';
        },

        job_name(value) {
            return value ? `<span style="font-weight:600;">${frappe.utils.escape_html(value)}</span>` : '';
        }
    }
};

function add_invoice_register_queue_buttons(listview) {
    const open_queue = (label, filters) => {
        listview.page.add_inner_button(__(label), function () {
            frappe.route_options = filters;
            frappe.set_route('List', 'Invoice Register Entry');
        }, __('Queues'));
    };

    open_queue('Needs Action', {
        status: ['in', [
            'Submitted for Approval',
            'Returned for Capture',
            'Query with Supplier',
            'Ready for Capture',
            'Drafted',
            'Returned to Draft'
        ]]
    });

    open_queue('Purchase Queue', {
        entry_type: 'Purchase',
        status: ['not in', ['Captured', 'Cancelled']]
    });

    open_queue('Sales Queue', {
        entry_type: 'Sales',
        status: ['not in', ['Issued to Client', 'Cancelled']]
    });

    open_queue('Completed', {
        status: ['in', ['Captured', 'Issued to Client']]
    });
}
