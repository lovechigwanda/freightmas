# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint


def service_orders_enabled():
	return cint(frappe.db.get_single_value("FreightMas Settings", "enable_service_orders"))


def service_order_required_before_pi():
	return service_orders_enabled() and cint(
		frappe.db.get_single_value("FreightMas Settings", "require_service_order_before_pi")
	)


def get_default_service_order_terms():
	return frappe.db.get_single_value("FreightMas Settings", "default_service_order_terms") or ""
