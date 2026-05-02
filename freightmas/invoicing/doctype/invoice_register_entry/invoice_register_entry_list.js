frappe.listview_settings['Invoice Register Entry'] = {
    get_indicator(doc) {
        const colours = {
            'Received': 'blue',
            'Submitted for Approval': 'orange',
            'Returned for Capture': 'blue',
            'Query with Supplier': 'red',
            'Ready for Capture': 'blue',
            'Captured': 'green',
            'Instruction Received': 'blue',
            'Drafted': 'orange',
            'Returned to Draft': 'orange',
            'Issued to Client': 'green',
            'Cancelled': 'grey'
        };
        return [__(doc.status), colours[doc.status] || 'grey', 'status,=,' + doc.status];
    }
};
