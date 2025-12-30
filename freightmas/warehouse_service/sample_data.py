#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

"""
Sample Data Generator for Warehouse Service Module

This script creates sample data for the Warehouse Service module.
Run this after migrating the database.

Usage:
    bench --site [site-name] execute freightmas.warehouse_service.sample_data.create_all_sample_data
"""

import frappe
from frappe.utils import today, add_days, now, nowdate, add_months


def create_all_sample_data():
	"""Create all sample data for Warehouse Service module"""
	frappe.set_user("Administrator")
	
	print("\n" + "="*60)
	print("Creating Sample Data for Warehouse Service Module")
	print("="*60 + "\n")
	
	# Create in correct order (masters first, then transactions)
	create_warehouse_bays()
	create_warehouse_bins()
	create_storage_unit_types()
	create_handling_activity_types()
	create_storage_rate_cards()
	create_customers()
	create_service_items()
	create_sample_goods_receipts()
	
	print("\n" + "="*60)
	print("✅ Sample Data Creation Complete!")
	print("="*60 + "\n")
	print("Next Steps:")
	print("1. Navigate to: Warehouse Service workspace")
	print("2. Review created masters and transactions")
	print("3. Open a Warehouse Job to see charges")
	print("4. Test creating a Goods Dispatch")
	print("\n")


def create_warehouse_zones():
	"""Create sample warehouse zones"""
	print("📦 Creating Warehouse Zones...")
	
	zones = [
		{
			"zone_code": "ZONE-A",
			"zone_name": "Zone A - Ambient Storage",
			"zone_type": "Ambient",
			"total_area_sqm": 500.00,
			"is_active": 1,
			"description": "<p>Main ambient temperature storage area for general goods</p>"
		},
		{
			"zone_code": "ZONE-B",
			"zone_name": "Zone B - Cold Storage",
			"zone_type": "Cold Storage",
			"total_area_sqm": 300.00,
			"is_active": 1,
			"description": "<p>Temperature controlled storage area (2-8°C)</p>"
		},
		{
			"zone_code": "ZONE-C",
			"zone_name": "Zone C - Open Yard",
			"zone_type": "Open Yard",
			"total_area_sqm": 1000.00,
			"is_active": 1,
			"description": "<p>Outdoor storage area for containers and oversized cargo</p>"
		},
		{
			"zone_code": "ZONE-D",
			"zone_name": "Zone D - Hazmat Storage",
			"zone_type": "Hazmat",
			"total_area_sqm": 200.00,
			"is_active": 1,
			"description": "<p>Hazardous materials storage with safety compliance</p>"
		}
	]
	
	for zone_data in zones:
		if not frappe.db.exists("Warehouse Zone", zone_data["zone_code"]):
			zone = frappe.get_doc({
				"doctype": "Warehouse Zone",
				**zone_data
			})
			zone.insert(ignore_permissions=True)
			print(f"  ✓ Created: {zone.zone_code} - {zone.zone_name}")
		else:
			print(f"  ⊙ Already exists: {zone_data['zone_code']}")


def create_warehouse_bays():
	"""Create sample warehouse bays"""
	print("\n🏭 Creating Warehouse Bays...")
	
	bays = [
		# Zone A Bays - Pallet Racking (40 pallets, 20 tons, 400cm height)
		{"zone": "ZONE-A", "bay_code": "A-01", "bay_type": "Pallet Racking", "capacity_sqm": 100.0, "max_pallets": 40, "max_weight_kg": 20000, "max_height_cm": 400},
		{"zone": "ZONE-A", "bay_code": "A-02", "bay_type": "Pallet Racking", "capacity_sqm": 100.0, "max_pallets": 40, "max_weight_kg": 20000, "max_height_cm": 400},
		# Floor Storage (30 pallets, 22.5 tons, 300cm height)
		{"zone": "ZONE-A", "bay_code": "A-03", "bay_type": "Floor Storage", "capacity_sqm": 150.0, "max_pallets": 60, "max_weight_kg": 22500, "max_height_cm": 300},
		# Shelving (10 pallets, 5 tons, 250cm height)
		{"zone": "ZONE-A", "bay_code": "A-04", "bay_type": "Shelving", "capacity_sqm": 50.0, "max_pallets": 10, "max_weight_kg": 5000, "max_height_cm": 250},
		
		# Zone B Bays - Pallet Racking
		{"zone": "ZONE-B", "bay_code": "B-01", "bay_type": "Pallet Racking", "capacity_sqm": 80.0, "max_pallets": 30, "max_weight_kg": 15000, "max_height_cm": 400},
		# Drive-In Racking (40 pallets, 20 tons, 400cm height)
		{"zone": "ZONE-B", "bay_code": "B-02", "bay_type": "Drive-In Racking", "capacity_sqm": 100.0, "max_pallets": 30, "max_weight_kg": 20000, "max_height_cm": 400},
		
		# Zone C Bays - Large Floor Storage (100 pallets each, 50 tons, 400cm height)
		{"zone": "ZONE-C", "bay_code": "C-01", "bay_type": "Floor Storage", "capacity_sqm": 500.0, "max_pallets": 500, "max_weight_kg": 60000, "max_height_cm": 400},
		{"zone": "ZONE-C", "bay_code": "C-02", "bay_type": "Floor Storage", "capacity_sqm": 500.0, "max_pallets": 500, "max_weight_kg": 60000, "max_height_cm": 400},
		
		# Zone D Bays
		{"zone": "ZONE-D", "bay_code": "D-01", "bay_type": "Pallet Racking", "capacity_sqm": 60.0, "max_pallets": 20, "max_weight_kg": 12000, "max_height_cm": 400},
		{"zone": "ZONE-D", "bay_code": "D-02", "bay_type": "Floor Storage", "capacity_sqm": 80.0, "max_pallets": 30, "max_weight_kg": 18000, "max_height_cm": 300},
	]
	
	for bay_data in bays:
		if not frappe.db.exists("Warehouse Bay", bay_data["bay_code"]):
			bay = frappe.get_doc({
				"doctype": "Warehouse Bay",
				"is_available": 1,
				**bay_data
			})
			bay.insert(ignore_permissions=True)
			print(f"  ✓ Created: {bay.bay_code} in {bay.zone}")
		else:
			print(f"  ⊙ Already exists: {bay_data['bay_code']}")


def create_warehouse_bins():
	"""Create sample warehouse bins"""
	print("\n📍 Creating Warehouse Bins...")
	
	bins_created = 0
	
	# Create bins for each bay
	# Capacity settings vary by bin type:
	# - Pallet Position: 20 pallets capacity (or 2 pallet positions)
	# - Floor Space: 30 pallets capacity
	# - Shelf: 10 pallets capacity
	bay_bin_configs = {
		"A-01": {"zone": "ZONE-A", "positions": 20, "type": "Pallet Position", "max_weight": 1000, "capacity_uom": "Pallets", "max_capacity": 2.0},
		"A-02": {"zone": "ZONE-A", "positions": 20, "type": "Pallet Position", "max_weight": 1000, "capacity_uom": "Pallets", "max_capacity": 2.0},
		"A-03": {"zone": "ZONE-A", "positions": 15, "type": "Floor Space", "max_weight": 1500, "capacity_uom": "Pallets", "max_capacity": 4.0},
		"A-04": {"zone": "ZONE-A", "positions": 10, "type": "Shelf", "max_weight": 500, "capacity_uom": "Pallets", "max_capacity": 1.0},
		"B-01": {"zone": "ZONE-B", "positions": 15, "type": "Pallet Position", "max_weight": 1000, "capacity_uom": "Pallets", "max_capacity": 2.0},
		"B-02": {"zone": "ZONE-B", "positions": 15, "type": "Pallet Position", "max_weight": 1000, "capacity_uom": "Pallets", "max_capacity": 2.0},
		"C-01": {"zone": "ZONE-C", "positions": 20, "type": "Floor Space", "max_weight": 3000, "capacity_uom": "SQM", "max_capacity": 25.0},
		"C-02": {"zone": "ZONE-C", "positions": 20, "type": "Floor Space", "max_weight": 3000, "capacity_uom": "SQM", "max_capacity": 25.0},
		"D-01": {"zone": "ZONE-D", "positions": 10, "type": "Pallet Position", "max_weight": 800, "capacity_uom": "Pallets", "max_capacity": 2.0},
		"D-02": {"zone": "ZONE-D", "positions": 10, "type": "Floor Space", "max_weight": 1200, "capacity_uom": "CBM", "max_capacity": 6.0},
	}
	
	for bay_code, config in bay_bin_configs.items():
		for position in range(1, config["positions"] + 1):
			bin_code = f"{bay_code}-{position:02d}"
			
			if not frappe.db.exists("Warehouse Bin", bin_code):
				bin_doc = frappe.get_doc({
					"doctype": "Warehouse Bin",
					"zone": config["zone"],
					"bay": bay_code,
					"bin_code": bin_code,
					"bin_type": config["type"],
					"max_weight_kg": config["max_weight"],
					"max_height_cm": 200.0,
					"is_occupied": 0,
					# Capacity management fields
					"capacity_uom": config["capacity_uom"],
					"max_capacity": config["max_capacity"]
				})
				bin_doc.insert(ignore_permissions=True)
				bins_created += 1
	
	print(f"  ✓ Created {bins_created} warehouse bins")


def create_storage_unit_types():
	"""Create sample storage unit types"""
	print("\n📦 Creating Storage Unit Types...")
	
	unit_types = [
		{
			"unit_type": "Euro Pallet",
			"standard_length_cm": 120.0,
			"standard_width_cm": 80.0,
			"standard_height_cm": 150.0,
			"standard_weight_kg": 500.0,
			"default_storage_rate_per_day": 5.00,
			"default_storage_rate_per_month": 120.00,
			"is_active": 1,
			"description": "Standard European pallet (1200mm x 800mm)",
			# Capacity conversion factors
			"pallet_equivalent_factor": 1.0,  # 1 pallet = 1 pallet
			"cbm_equivalent_factor": 1.44,  # 1.2m x 0.8m x 1.5m = 1.44 CBM
			"sqm_equivalent_factor": 0.96  # 1.2m x 0.8m = 0.96 SQM
		},
		{
			"unit_type": "IBC Container",
			"standard_length_cm": 100.0,
			"standard_width_cm": 100.0,
			"standard_height_cm": 120.0,
			"standard_weight_kg": 1000.0,
			"default_storage_rate_per_day": 8.00,
			"default_storage_rate_per_month": 200.00,
			"is_active": 1,
			"description": "Intermediate Bulk Container (1000L capacity)",
			# Capacity conversion factors
			"pallet_equivalent_factor": 1.2,  # Slightly larger than 1 pallet
			"cbm_equivalent_factor": 1.2,  # 1.0m x 1.0m x 1.2m = 1.2 CBM
			"sqm_equivalent_factor": 1.0  # 1.0m x 1.0m = 1.0 SQM
		},
		{
			"unit_type": "Carton Box",
			"standard_length_cm": 40.0,
			"standard_width_cm": 30.0,
			"standard_height_cm": 30.0,
			"standard_weight_kg": 20.0,
			"default_storage_rate_per_day": 0.50,
			"default_storage_rate_per_month": 12.00,
			"is_active": 1,
			"description": "Standard cardboard carton box",
			# Capacity conversion factors
			"pallet_equivalent_factor": 0.1,  # ~10 cartons fit on 1 pallet
			"cbm_equivalent_factor": 0.036,  # 0.4m x 0.3m x 0.3m = 0.036 CBM
			"sqm_equivalent_factor": 0.12  # 0.4m x 0.3m = 0.12 SQM
		},
		{
			"unit_type": "Pallet Cage",
			"standard_length_cm": 120.0,
			"standard_width_cm": 100.0,
			"standard_height_cm": 180.0,
			"standard_weight_kg": 600.0,
			"default_storage_rate_per_day": 6.00,
			"default_storage_rate_per_month": 150.00,
			"is_active": 1,
			"description": "Metal pallet cage for secure storage",
			# Capacity conversion factors
			"pallet_equivalent_factor": 1.25,  # Slightly larger than euro pallet
			"cbm_equivalent_factor": 2.16,  # 1.2m x 1.0m x 1.8m = 2.16 CBM
			"sqm_equivalent_factor": 1.2  # 1.2m x 1.0m = 1.2 SQM
		},
		{
			"unit_type": "Drum (200L)",
			"standard_length_cm": 60.0,
			"standard_width_cm": 60.0,
			"standard_height_cm": 90.0,
			"standard_weight_kg": 200.0,
			"default_storage_rate_per_day": 3.00,
			"default_storage_rate_per_month": 75.00,
			"is_active": 1,
			"description": "200 liter steel drum",
			# Capacity conversion factors
			"pallet_equivalent_factor": 0.38,  # ~4 drums on 1 pallet (0.6x0.6 = 0.36 sqm each)
			"cbm_equivalent_factor": 0.324,  # 0.6m x 0.6m x 0.9m = 0.324 CBM
			"sqm_equivalent_factor": 0.36  # 0.6m x 0.6m = 0.36 SQM
		}
	]
	
	for unit_data in unit_types:
		if not frappe.db.exists("Storage Unit Type", unit_data["unit_type"]):
			unit = frappe.get_doc({
				"doctype": "Storage Unit Type",
				**unit_data
			})
			unit.insert(ignore_permissions=True)
			print(f"  ✓ Created: {unit.unit_type}")
		else:
			print(f"  ⊙ Already exists: {unit_data['unit_type']}")


def create_handling_activity_types():
	"""Create sample handling activity types"""
	print("\n🔧 Creating Handling Activity Types...")
	
	activities = [
		{
			"activity_code": "OFFLOAD",
			"activity_name": "Offloading - Container",
			"category": "Inbound",
			"default_rate": 150.00,
			"unit_of_measure": "Per Container",
			"is_active": 1,
			"description": "<p>Offloading goods from container to warehouse</p>"
		},
		{
			"activity_code": "LOAD",
			"activity_name": "Loading - Truck",
			"category": "Outbound",
			"default_rate": 100.00,
			"unit_of_measure": "Per Truck",
			"is_active": 1,
			"description": "<p>Loading goods from warehouse to truck</p>"
		},
		{
			"activity_code": "LABEL",
			"activity_name": "Labelling Service",
			"category": "Value-Added",
			"default_rate": 2.00,
			"unit_of_measure": "Per Carton",
			"is_active": 1,
			"description": "<p>Labelling and marking of cartons/pallets</p>"
		},
		{
			"activity_code": "INSPECT",
			"activity_name": "Quality Inspection",
			"category": "Value-Added",
			"default_rate": 50.00,
			"unit_of_measure": "Per Hour",
			"is_active": 1,
			"description": "<p>Quality inspection and verification of goods</p>"
		},
		{
			"activity_code": "REPACK",
			"activity_name": "Repackaging Service",
			"category": "Value-Added",
			"default_rate": 5.00,
			"unit_of_measure": "Per Carton",
			"is_active": 1,
			"description": "<p>Repackaging and consolidation services</p>"
		},
		{
			"activity_code": "RELOCATE",
			"activity_name": "Internal Relocation",
			"category": "Internal",
			"default_rate": 10.00,
			"unit_of_measure": "Per Pallet",
			"is_active": 1,
			"description": "<p>Moving goods within warehouse for space optimization</p>"
		}
	]
	
	for activity_data in activities:
		if not frappe.db.exists("Handling Activity Type", activity_data["activity_code"]):
			activity = frappe.get_doc({
				"doctype": "Handling Activity Type",
				**activity_data
			})
			activity.insert(ignore_permissions=True)
			print(f"  ✓ Created: {activity.activity_code} - {activity.activity_name}")
		else:
			print(f"  ⊙ Already exists: {activity_data['activity_code']}")


def create_storage_rate_cards():
	"""Create sample storage rate cards"""
	print("\n💳 Creating Storage Rate Cards...")
	
	rate_cards = [
		{
			"rate_card_name": "Standard Rates 2025",
			"customer": None,
			"valid_from": "2025-01-01",
			"valid_to": "2025-12-31",
			"currency": "USD",
			"is_default": 1,
			"description": "<p>Standard storage rates for all customers - 2025</p>",
			"rate_items": [
				{"storage_unit_type": "Euro Pallet", "zone_type": "Ambient", "rate_per_day": 5.00, "rate_per_month": 120.00, "free_days": 0},
				{"storage_unit_type": "Euro Pallet", "zone_type": "Cold Storage", "rate_per_day": 8.00, "rate_per_month": 200.00, "free_days": 0},
				{"storage_unit_type": "Euro Pallet", "zone_type": "Hazmat", "rate_per_day": 10.00, "rate_per_month": 250.00, "free_days": 0},
				{"storage_unit_type": "IBC Container", "zone_type": "Ambient", "rate_per_day": 8.00, "rate_per_month": 200.00, "free_days": 0},
				{"storage_unit_type": "IBC Container", "zone_type": "Hazmat", "rate_per_day": 12.00, "rate_per_month": 300.00, "free_days": 0},
				{"storage_unit_type": "Carton Box", "zone_type": "Ambient", "rate_per_day": 0.50, "rate_per_month": 12.00, "free_days": 0},
				{"storage_unit_type": "Pallet Cage", "zone_type": "Ambient", "rate_per_day": 6.00, "rate_per_month": 150.00, "free_days": 0},
				{"storage_unit_type": "Drum (200L)", "zone_type": "Hazmat", "rate_per_day": 4.00, "rate_per_month": 100.00, "free_days": 0},
			]
		}
	]
	
	for card_data in rate_cards:
		if not frappe.db.exists("Storage Rate Card", card_data["rate_card_name"]):
			rate_items = card_data.pop("rate_items")
			
			card = frappe.get_doc({
				"doctype": "Storage Rate Card",
				**card_data
			})
			
			for item_data in rate_items:
				card.append("rate_items", item_data)
			
			card.insert(ignore_permissions=True)
			print(f"  ✓ Created: {card.rate_card_name} with {len(rate_items)} rate items")
		else:
			print(f"  ⊙ Already exists: {card_data['rate_card_name']}")


def create_customers():
	"""Create sample customers if they don't exist"""
	print("\n👥 Creating Sample Customers...")
	
	customers = [
		{"customer_name": "ABC Electronics Ltd", "customer_type": "Company", "customer_group": "Commercial"},
		{"customer_name": "XYZ Pharmaceuticals", "customer_type": "Company", "customer_group": "Commercial"},
		{"customer_name": "Global Trading Co", "customer_type": "Company", "customer_group": "Commercial"},
	]
	
	for customer_data in customers:
		if not frappe.db.exists("Customer", customer_data["customer_name"]):
			customer = frappe.get_doc({
				"doctype": "Customer",
				**customer_data
			})
			customer.insert(ignore_permissions=True)
			print(f"  ✓ Created customer: {customer.customer_name}")
		else:
			print(f"  ⊙ Customer already exists: {customer_data['customer_name']}")


def create_service_items():
	"""Create service items for invoicing"""
	print("\n🛍️ Creating Service Items...")
	
	items = [
		{
			"item_code": "WMS-STORAGE",
			"item_name": "Warehouse Storage Service",
			"item_group": "Services",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_service_item": 1,
			"description": "Warehouse storage service - charged per day/month based on storage unit type"
		},
		{
			"item_code": "WMS-HANDLING",
			"item_name": "Warehouse Handling Service",
			"item_group": "Services",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_service_item": 1,
			"description": "Warehouse handling service - includes offloading, loading, and value-added services"
		}
	]
	
	for item_data in items:
		if not frappe.db.exists("Item", item_data["item_code"]):
			item = frappe.get_doc({
				"doctype": "Item",
				**item_data
			})
			item.insert(ignore_permissions=True)
			print(f"  ✓ Created service item: {item.item_code}")
		else:
			print(f"  ⊙ Service item already exists: {item_data['item_code']}")


def create_sample_goods_receipts():
	"""Create sample goods receipts with items"""
	print("\n📥 Creating Sample Goods Receipts...")
	
	# Get customers
	customers = frappe.get_all("Customer", filters={"customer_name": ["in", ["ABC Electronics Ltd", "XYZ Pharmaceuticals", "Global Trading Co"]]}, pluck="name")
	
	if not customers:
		print("  ⚠ No customers found. Skipping goods receipts.")
		return
	
	receipts_data = [
		{
			"customer": customers[0] if len(customers) > 0 else None,
			"receipt_date": add_days(today(), -30),
			"reference_number": "PO-2024-001",
			"transporter": None,
			"vehicle_number": "ABC-1234",
			"driver_name": "John Doe",
			"driver_contact": "+1234567890",
			"storage_instructions": "Store in ambient conditions, keep dry",
			"handling_instructions": "Handle with care - fragile electronics",
			"items": [
				{
					"customer_reference": "SKU-ELEC-001",
					"description": "Electronic Components - Laptops",
					"storage_unit_type": "Euro Pallet",
					"quantity": 10,
					"weight_kg": 500,
					"length_cm": 120,
					"width_cm": 80,
					"height_cm": 150,
					"warehouse_zone": "ZONE-A",
					"warehouse_bay": "A-01",
					"warehouse_bin": "A-01-01",
					"special_handling": "Fragile"
				},
				{
					"customer_reference": "SKU-ELEC-002",
					"description": "Electronic Components - Monitors",
					"storage_unit_type": "Euro Pallet",
					"quantity": 8,
					"weight_kg": 400,
					"length_cm": 120,
					"width_cm": 80,
					"height_cm": 150,
					"warehouse_zone": "ZONE-A",
					"warehouse_bay": "A-01",
					"warehouse_bin": "A-01-02",
					"special_handling": "Fragile"
				}
			]
		},
		{
			"customer": customers[1] if len(customers) > 1 else customers[0],
			"receipt_date": add_days(today(), -20),
			"reference_number": "PO-2024-002",
			"transporter": None,
			"vehicle_number": "XYZ-5678",
			"driver_name": "Jane Smith",
			"driver_contact": "+9876543210",
			"storage_instructions": "Maintain cold chain at 2-8°C",
			"handling_instructions": "Temperature sensitive - handle quickly",
			"items": [
				{
					"customer_reference": "PHARMA-MED-001",
					"description": "Pharmaceutical Products - Vaccines",
					"storage_unit_type": "Pallet Cage",
					"quantity": 5,
					"weight_kg": 300,
					"length_cm": 120,
					"width_cm": 100,
					"height_cm": 180,
					"warehouse_zone": "ZONE-B",
					"warehouse_bay": "B-01",
					"warehouse_bin": "B-01-01",
					"expiry_date": add_months(today(), 6),
					"special_handling": "Temperature Controlled"
				}
			]
		},
		{
			"customer": customers[2] if len(customers) > 2 else customers[0],
			"receipt_date": add_days(today(), -10),
			"reference_number": "PO-2024-003",
			"transporter": None,
			"vehicle_number": "GTR-9012",
			"driver_name": "Mike Johnson",
			"driver_contact": "+1122334455",
			"storage_instructions": "General storage conditions",
			"handling_instructions": "Standard handling procedures",
			"items": [
				{
					"customer_reference": "TRADE-GEN-001",
					"description": "General Merchandise - Consumer Goods",
					"storage_unit_type": "Euro Pallet",
					"quantity": 15,
					"weight_kg": 750,
					"length_cm": 120,
					"width_cm": 80,
					"height_cm": 150,
					"warehouse_zone": "ZONE-A",
					"warehouse_bay": "A-02",
					"warehouse_bin": "A-02-01",
					"special_handling": "None"
				},
				{
					"customer_reference": "TRADE-GEN-002",
					"description": "General Merchandise - Textiles",
					"storage_unit_type": "Carton Box",
					"quantity": 100,
					"weight_kg": 200,
					"length_cm": 40,
					"width_cm": 30,
					"height_cm": 30,
					"warehouse_zone": "ZONE-A",
					"warehouse_bay": "A-04",
					"warehouse_bin": "A-04-01",
					"special_handling": "None"
				}
			]
		}
	]
	
	for receipt_data in receipts_data:
		if not receipt_data["customer"]:
			continue
			
		items_data = receipt_data.pop("items")
		
		# Create receipt
		receipt = frappe.get_doc({
			"doctype": "Customer Goods Receipt",
			"naming_series": "WMS-GRN-.YYYY.-",
			"status": "Draft",
			**receipt_data
		})
		
		# Add items
		for item_data in items_data:
			receipt.append("items", item_data)
		
		receipt.insert(ignore_permissions=True)
		receipt.submit()
		
		print(f"  ✓ Created and submitted: {receipt.name} for {receipt.customer}")
		print(f"    - {len(items_data)} items received")
		print(f"    - Warehouse Job: {receipt.warehouse_job}")


if __name__ == "__main__":
	create_all_sample_data()
