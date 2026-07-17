# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

# One independent numbering series per service module, e.g. PC-00001, BC-00001.
SERVICE_MODULE_PREFIXES = {
	"Sea/Air Freight": "SEA",
	"Road Freight": "RDF",
	"Port Clearance": "PC",
	"Road Transport": "RT",
	"Border Clearance": "BC",
	"Warehouse": "WH",
}


class MilestoneDefinition(Document):
	def autoname(self):
		prefix = SERVICE_MODULE_PREFIXES.get(self.service_module, "MS")
		self.name = make_autoname(f"{prefix}-.#####")
		if not self.milestone_code:
			self.milestone_code = self.name

	def validate(self):
		self.milestone_code = (self.milestone_code or "").strip().upper().replace(" ", "_")
