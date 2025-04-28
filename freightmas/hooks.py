app_name = "freightmas"
app_title = "FreightMas"
app_publisher = "Zvomaita Technologies (Pvt) Ltd"
app_description = "Freight Management System"
app_email = "info@zvomaita.co.zw"
app_license = "mit"

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
# app_include_js = "/assets/freightmas/js/freightmas.js"

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

# scheduler_events = {
# 	"all": [
# 		"freightmas.tasks.all"
# 	],
# 	"daily": [
# 		"freightmas.tasks.daily"
# 	],
# 	"hourly": [
# 		"freightmas.tasks.hourly"
# 	],
# 	"weekly": [
# 		"freightmas.tasks.weekly"
# 	],
# 	"monthly": [
# 		"freightmas.tasks.monthly"
# 	],
# }

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

##REGISTER BEFORE DELETE AND VALIDATE FOR TRIP REVENUE CHARGES

doc_events = {
    "Trip Revenue Charges": {
        "validate": "freightmas.trucking_service.doctype.trip_revenue_charges.trip_revenue_charges.validate",
        "before_delete": "freightmas.trucking_service.doctype.trip_revenue_charges.trip_revenue_charges.before_delete"
    }
}

##############################################################

##REGISTER BEFORE DELETE AND VALIDATE FOR TRIP COST CHARGES

doc_events = {
    "Trip Cost Charges": {
        "validate": "freightmas.trucking_service.doctype.trip_cost_charges.trip_cost_charges.validate",
        "before_delete": "freightmas.trucking_service.doctype.trip_cost_charges.trip_cost_charges.before_delete"
    }
}


################################################################

###FIXTURES

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["name", "in", [
                "Purchase Receipt-custom_reference",
                "Journal Entry-custom_trip_reference",
                "Stock Entry-custom_trip_reference",
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
                "Vehicle-custom_is_horse"
            ]]
        ]
    },
    {
        "dt": "Workflow"
    },
    {
        "dt": "Workflow State"
    },
    {
        "dt": "Workflow Action"
    },
    {
        "dt": "Workspace"
    },
    {
        "dt": "Print Format"
    }
]


#############################################################################

doc_events = {
    "Driver": {
        "before_insert": "freightmas.hooks.create_driver_advance_account"
    }
}

#############################################################################

# Hook on Driver doctype
def create_driver_advance_account(doc, method):
    import frappe

    settings = frappe.get_single("FreightMas Settings")

    # Create Advance Account
    if not doc.driver_advance_account:
        create_child_account(
            account_type="advance",
            driver_name=doc.full_name,
            settings_account=settings.driver_advance_parent_account,
            field_to_set="driver_advance_account",
            doc=doc
        )

    # Create Bonus Account
    if not doc.driver_bonus_account:
        create_child_account(
            account_type="bonus",
            driver_name=doc.full_name,
            settings_account=settings.driver_bonus_parent_account,
            field_to_set="driver_bonus_account",
            doc=doc
        )


def create_child_account(account_type, driver_name, settings_account, field_to_set, doc):
    import frappe

    if not settings_account:
        frappe.throw(f"Please set the Driver {account_type.title()} Parent Account in FreightMas Settings.")

    account_name = f"{driver_name} {account_type.title()}"
    existing_account = frappe.db.exists("Account", {
        "account_name": account_name,
        "parent_account": settings_account
    })

    if not existing_account:
        new_account = frappe.get_doc({
            "doctype": "Account",
            "account_name": account_name,
            "parent_account": settings_account,
            "company": frappe.db.get_value("Account", settings_account, "company"),
            "is_group": 0,
            "report_type": "Balance Sheet",
            "root_type": "Asset"
        })
        new_account.insert()

        # Set the new account back to the Driver doc
        setattr(doc, field_to_set, new_account.name)


#############################################################################

after_install = "freightmas.hooks.create_driver_party_type"

#############################################################################


def create_driver_party_type():
    import frappe

    if not frappe.db.exists("Party Type", "Driver"):
        frappe.get_doc({
            "doctype": "Party Type",
            "party_type": "Driver",
            "reference_doctype": "Driver",
            "disabled": 0
        }).insert(ignore_permissions=True)


###########################################################################