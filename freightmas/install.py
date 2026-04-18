import frappe


def after_install():
	create_default_container_types()


def create_default_container_types():
	containers = [
		{"container_full_name": "20ft Standard Dry", "container_name": "20SD", "iso_code": "22G1", "size": "20ft", "container_description": "General purpose container for most cargo"},
		{"container_full_name": "40ft Standard Dry", "container_name": "40SD", "iso_code": "42G1", "size": "40ft", "container_description": "Larger general cargo container"},
		{"container_full_name": "40ft High Cube Dry", "container_name": "40HC", "iso_code": "45G1", "size": "40ft HC", "container_description": "Extra height container (9'6\") for bulky cargo"},
		{"container_full_name": "20ft Reefer", "container_name": "20RF", "iso_code": "22R1", "size": "20ft", "container_description": "Temperature-controlled container for perishable goods"},
		{"container_full_name": "40ft Reefer", "container_name": "40RF", "iso_code": "42R1", "size": "40ft", "container_description": "Larger refrigerated container"},
		{"container_full_name": "40ft High Cube Reefer", "container_name": "40HR", "iso_code": "45R1", "size": "40ft HC", "container_description": "High cube refrigerated container"},
		{"container_full_name": "20ft Open Top", "container_name": "20OT", "iso_code": "22U1", "size": "20ft", "container_description": "Open roof for loading oversized cargo from above"},
		{"container_full_name": "40ft Open Top", "container_name": "40OT", "iso_code": "42U1", "size": "40ft", "container_description": "Larger open top container"},
		{"container_full_name": "20ft Flat Rack", "container_name": "20FR", "iso_code": "22P1", "size": "20ft", "container_description": "No side walls, used for heavy or oversized cargo"},
		{"container_full_name": "40ft Flat Rack", "container_name": "40FR", "iso_code": "42P1", "size": "40ft", "container_description": "Larger flat rack for out-of-gauge cargo"},
		{"container_full_name": "Tank Container", "container_name": "20TK", "iso_code": "22T1", "size": "20ft", "container_description": "Used for transporting liquids, chemicals, or gases"},
		{"container_full_name": "Ventilated Container", "container_name": "20VT", "iso_code": "22V1", "size": "20ft", "container_description": "Allows airflow for cargo like coffee or cocoa"},
		{"container_full_name": "Platform Container", "container_name": "20PL", "iso_code": "22P3", "size": "20ft", "container_description": "Base platform only for extreme oversized cargo"},
	]

	for ct in containers:
		if not frappe.db.exists("Container Type", ct["container_name"]):
			doc = frappe.get_doc({"doctype": "Container Type", **ct})
			doc.insert(ignore_permissions=True)

	frappe.db.commit()
