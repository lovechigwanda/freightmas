app_name = "freightmas"
app_title = "FreightMas"
app_publisher = "Zvomaita Technologies (Pvt) Ltd"
app_description = "Freight Management System"
app_email = "info@zvomaita.co.zw"
app_license = "mit"

import frappe

def clear_old_workspaces():
    """Delete only FreightMas-related Workspace records before importing fixtures"""
    frappe.db.sql("""
        DELETE FROM `tabWorkspace`
        WHERE name IN ('Port Clearing Service', 'Road Freight Service', 'Forwarding Service', 'FreightMas Sales', 'Trucking Service')
    """)
    frappe.db.commit()

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "freightmas",
# 		"logo": "/assets/freightmas/logo.png",
# 		"title": "FreightMas",
# 		"route": "/freightmas",
# 		"has_permission": "freightmas.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/freightmas/css/freightmas.css"
app_include_js = "/assets/freightmas/js/report_commons.js"

# include js, css files in header of web template
# web_include_css = "/assets/freightmas/css/freightmas.css"
# web_include_js = "/assets/freightmas/js/freightmas.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "freightmas/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "freightmas/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "freightmas.utils.jinja_methods",
# 	"filters": "freightmas.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "freightmas.install.before_install"
# after_install = "freightmas.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "freightmas.uninstall.before_uninstall"
# after_uninstall = "freightmas.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "freightmas.utils.before_app_install"
# after_app_install = "freightmas.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "freightmas.utils.before_app_uninstall"
# after_app_uninstall = "freightmas.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "freightmas.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"freightmas.scheduler.quotation.expire_quotations"
	],
	"monthly": [
		"freightmas.warehouse_service.doctype.warehouse_job.warehouse_job.calculate_all_monthly_storage"
	],
}

# Testing
# -------

# before_tests = "freightmas.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "freightmas.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "freightmas.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["freightmas.utils.before_request"]
# after_request = ["freightmas.utils.after_request"]

# Job Events
# ----------
# before_job = ["freightmas.utils.before_job"]
# after_job = ["freightmas.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"freightmas.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }



##############################################################

##DOCUMENT EVENTS CONFIGURATION

doc_events = {
    "Trip Revenue Charges": {
        "validate": "freightmas.trucking_service.doctype.trip_revenue_charges.trip_revenue_charges.validate",
        "before_delete": "freightmas.trucking_service.doctype.trip_revenue_charges.trip_revenue_charges.before_delete"
    },
    "Trip Cost Charges": {
        "validate": "freightmas.trucking_service.doctype.trip_cost_charges.trip_cost_charges.validate",
        "before_delete": "freightmas.trucking_service.doctype.trip_cost_charges.trip_cost_charges.before_delete"
    },
    "Forwarding Job": {
        "after_insert": "freightmas.utils.forwarding_job_folder.create_job_folder_on_insert",
        "on_update": "freightmas.utils.forwarding_job_folder.update_job_folder_on_update", 
        "before_rename": "freightmas.utils.forwarding_job_folder.before_rename_forwarding_job"
    },
    "File": {
        "after_insert": "freightmas.utils.forwarding_job_folder.file_on_insert",
        "on_update": "freightmas.utils.forwarding_job_folder.file_on_update"
    },
    "Quotation": {
		"validate": "freightmas.utils.quotation.validate_quotation",
		"on_update_after_submit": "freightmas.utils.quotation.on_quotation_workflow_change"
	}
}


################################################################

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["name", "in", [
                "Driver-custom_advance_account",
                "Driver-custom_bonus_account",
                "Stock Entry-custom_trip_reference",
                "Purchase Receipt-custom_reference",
                "Journal Entry-custom_trip_reference",
                "Driver-custom_passport_number",
                "Driver-custom_passport_issue_date",
                "Driver-custom_passport_expiry_date",
                "Driver-custom_cellphone_number_2",
                "Purchase Invoice-custom_trip_reference",
                "Purchase Invoice-custom_is_trip_invoice",
                "Sales Invoice-custom_trip_reference",
                "Sales Invoice-custom_is_trip_invoice",
                "Trip-workflow_state",
                "Vehicle-custom_is_trailer",
                "Vehicle-custom_is_horse",
                "Sales Invoice-custom_clearing_job_reference",
                "Sales Invoice-custom_is_clearing_invoice",
                "Purchase Invoice-custom_clearing_job_reference",
                "Purchase Invoice-custom_is_clearing_invoice",
                "Sales Invoice-custom_forwarding_job_reference",
                "Sales Invoice-custom_is_forwarding_invoice",
                "Purchase Invoice-custom_forwarding_job_reference",
                "Purchase Invoice-custom_is_forwarding_invoice",
                "Sales Invoice-custom_road_freight_job_reference",
                "Sales Invoice-custom_is_road_freight_invoice",
                "Sales Invoice-custom_is_warehouse_invoice",
                "Sales Invoice-custom_warehouse_job_reference",               
                "Sales Invoice-custom_bundle_charges",
                "Purchase Invoice-custom_road_freight_job_reference",
                "Purchase Invoice-custom_is_road_freight_invoice",
                "Sales Invoice-custom_banking_details",
                "Quotation-custom_job_description",
                "Quotation-custom_destination_port", 
                "Quotation-custom_origin_port",
                "Quotation-custom_job_type",
                "Quotation-custom_is_freight_quote",
                "Quotation Item-custom_supplier",
                "Quotation Item-custom_cost_amount",
                "Quotation-custom_est_cost",
                "Quotation-custom_est_revenue",
                "Quotation-custom_est_profit",
                "Quotation-custom_quotation_cost_col_break",
                "Quotation-custom_quotation_cost_col_break_2",
                "Quotation-custom_quotation_costing_totals",
                "Quotation-custom_job_order_reference",
                "Quotation Item-custom_buy_rate",
                "Quotation Item-custom_job_reference",
                "Quotation-custom_bundle_charges",
                "Quotation-custom_customer_reference",
                "Customer-custom_auto_tracking_email",
                "Customer-custom_enable_tracking_emails",
                "Customer-custom_cc_recipients",
                "Customer-custom_primary_tracking_email",
                "Customer-custom_tracking_email_settings"
            ]]
        ]
    },
    {
        "dt": "Workflow",
        "filters": [
            ["name", "=", "Quotation Workflow"]
        ]
    },
    {
        "dt": "Workflow State",
        "filters": [
            ["name", "in", ["Draft", "Pending Approval", "Approved", "Sent to Customer", "Accepted", "Rejected", "Expired","JO Created", "Cancelled"]]
        ]
    },
    {
        "dt": "Workflow Action Master",
        "filters": [
            ["name", "in", ["Submit for Approval", "Approve", "Reject", "Send to Customer", "Mark Accepted", "Mark Rejected", "Mark Expired", "Cancel"]]
        ]
    },
    {
        "dt": "Workspace",
        "filters": [
            ["name", "in", ["Port Clearing Service", "Road Freight Service", "Forwarding Service","FreightMas Accounts","Warehouse Service","FreightMas Sales","Trucking Service"]]
        ]
    },
    #{
    #    "dt": "Letter Head",
    #    "filters": [
    #        ["name", "in", ["Main Letterhead"]]
    #    ]
    #},
    {
        "dt": "Print Format",
        "filters": [
            ["name", "in", [
                "Quotation Cost Sheet",
                "FreightMas TBSI",
                "FreightMas Sales Invoice",
                "FreightMas Quotation",
                "Forwarding Job Cost Sheet",
                "Road Freight Job Cost Sheet",
                "Clearing Job Cost Sheet",
                "FreightMas Purchase Invoice",
                "FM Subs",
                "Trip Bulk Sales Invoice",
                "Cash Pmt Voucher",
                "Trip Sales Invoice"

            ]]
        ]
    }
]


doctype_js = {
    "Quotation": "public/js/quotation.js"
}
