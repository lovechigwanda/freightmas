import frappe
from frappe.model.document import Document


class DNDStorageRateCard(Document):
	def validate(self):
		if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
			frappe.throw("Valid From date cannot be after Valid To date.")

		# Enforce uniqueness: no two active cards for same SL + port + direction
		self._check_duplicate()

	def _check_duplicate(self):
		filters = {
			"shipping_line": self.shipping_line,
			"port": self.port or "",
			"direction": self.direction or "",
			"is_active": 1,
			"name": ["!=", self.name],
		}
		duplicate = frappe.db.get_value("DND Storage Rate Card", filters, "name")
		if duplicate:
			frappe.throw(
				f"An active rate card already exists for this combination: {duplicate}. "
				"Deactivate it before creating a new one."
			)


@frappe.whitelist()
def fetch_container_types(rate_card_name):
	"""
	Populate container_rates child table with all active Container Types.
	Skips types already present. Returns updated doc name.
	"""
	doc = frappe.get_doc("DND Storage Rate Card", rate_card_name)
	existing = {row.container_type for row in doc.container_rates}

	all_types = frappe.get_all(
		"Container Type",
		filters={"is_active": 1},
		fields=["name", "container_full_name"],
		order_by="name asc",
	)

	added = 0
	for ct in all_types:
		if ct.name not in existing:
			doc.append("container_rates", {
				"container_type": ct.name,
				"dnd_rate_per_day": 0,
				"storage_rate_per_day": 0,
			})
			added += 1

	doc.save(ignore_permissions=True)
	return {"added": added, "total": len(doc.container_rates)}
