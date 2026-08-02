# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

# One independent numbering series per service module, e.g. PC-STG-00001,
# BC-STG-00001 - mirrors Milestone Definition's SERVICE_MODULE_PREFIXES.
SERVICE_MODULE_PREFIXES = {
	"Sea/Air Freight": "SEA",
	"Road Freight": "RDF",
	"Port Clearance": "PC",
	"Road Transport": "RT",
	"Border Clearance": "BC",
	"Warehouse": "WH",
}


class MilestoneStage(Document):
	def autoname(self):
		prefix = SERVICE_MODULE_PREFIXES.get(self.service_module, "MS")
		self.name = make_autoname(f"{prefix}-STG-.#####")
