from frappe import _


def get_data():
	return {
		"fieldname": "service_order_reference",
		"non_standard_fieldnames": {
			"Purchase Invoice": "service_order_reference",
		},
		"internal_links": {
			"Forwarding Job": "forwarding_job_reference",
		},
		"transactions": [
			{
				"label": _("Reference"),
				"items": ["Forwarding Job", "Purchase Invoice"],
			},
		],
	}
