# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Whitelisted API for the FreightMas Command Center shell.

This module is the home for cross-module concerns (branding, the top-level
Overview page) as the Command Center grows beyond Forwarding. Today it simply
delegates to the Forwarding module's existing, already-tested endpoints -
there's nothing else to aggregate yet. As Clearing/Trucking/Warehouse/etc.
dashboards are added, get_overview() should be expanded here to merge data
from each module instead of passing Forwarding's data straight through.
"""

import frappe

from freightmas.freightmas.page.shipment_dashboard.shipment_dashboard import (
	get_branding as _forwarding_get_branding,
	get_overview as _forwarding_get_overview,
)


@frappe.whitelist()
def get_branding():
	return _forwarding_get_branding()


@frappe.whitelist()
def get_overview():
	return _forwarding_get_overview()
