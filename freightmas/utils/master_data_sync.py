import frappe


def match_or_create_port(locode, name, country_code):
	"""Match a Searates port to a FreightMas Port by UN/LOCODE, or auto-create if missing.

	Args:
		locode: UN/LOCODE string e.g. "MZBEW"
		name: Port name from API e.g. "Beira"
		country_code: 2-letter ISO country code e.g. "MZ"

	Returns:
		Port name (str) if matched/created, or None if locode is empty
	"""
	if not locode:
		return None

	# Try to find by port_code (UN/LOCODE)
	port = frappe.db.get_value("Port", {"port_code": locode}, "name")
	if port:
		return port

	# Try to find by port_name (existing port without LOCODE set)
	if name:
		port = frappe.db.get_value("Port", {"port_name": name}, "name")
		if port:
			# Update existing port with the LOCODE
			frappe.db.set_value("Port", port, "port_code", locode)
			return port

	# Auto-create the port
	country = _resolve_country(country_code)

	doc = frappe.get_doc({
		"doctype": "Port",
		"port_name": name or locode,
		"port_code": locode,
		"country": country or "",
		"sea_port": 1,
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return doc.name


def _resolve_country(country_code):
	"""Resolve a 2-letter ISO country code to an ERPNext Country name."""
	if not country_code:
		return None
	# ERPNext stores code as lowercase
	return frappe.db.get_value("Country", {"code": country_code.lower()}, "name")


def match_container_type(iso_code, size_type=None):
	"""Match API container equipment to a FreightMas Container Type.

	Args:
		iso_code: ISO 6346 type code e.g. "42G1"
		size_type: Carrier shorthand e.g. "40HC" (Traqo fallback when iso_code is null)

	Returns:
		Container Type name (str) if matched, or None
	"""
	if iso_code:
		match = frappe.db.get_value("Container Type", {"iso_code": iso_code}, "name")
		if match:
			return match

	if size_type:
		normalized = str(size_type).strip().upper()
		if normalized:
			return frappe.db.get_value("Container Type", {"container_name": normalized}, "name")

	return None


def match_shipping_line(scac_code):
	"""Match a Searates SCAC code to a FreightMas Shipping Line.

	Args:
		scac_code: Standard Carrier Alpha Code e.g. "MSCU"

	Returns:
		Shipping Line name (str) if matched, or None
	"""
	if not scac_code:
		return None

	return frappe.db.get_value("Shipping Line", {"scac_code": scac_code}, "name")
