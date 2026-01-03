# Copyright (c) 2025, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_datetime_str, date_diff, today, getdate


class WarehouseJob(Document):
	def validate(self):
		"""Validate Warehouse Job"""
		self.validate_fiscal_year()
		self.validate_job_dates()
		self.calculate_job_validity()
		self.calculate_storage_charges()
		self.calculate_handling_charges()
		self.calculate_totals()
		self.validate_invoiced_rows()
	
	def validate_fiscal_year(self):
		"""Validate job dates fall within fiscal year"""
		if not self.fiscal_year:
			return
		
		# Get fiscal year dates
		fy = frappe.get_doc("Fiscal Year", self.fiscal_year)
		fy_start = getdate(fy.year_start_date)
		fy_end = getdate(fy.year_end_date)
		
		# Validate job start date
		if self.job_start_date:
			job_start = getdate(self.job_start_date)
			if job_start < fy_start:
				frappe.throw(f"Job Start Date cannot be before fiscal year start ({fy_start})")
			if job_start > fy_end:
				frappe.throw(f"Job Start Date cannot be after fiscal year end ({fy_end})")
		
		# Validate job end date
		if self.job_end_date:
			job_end = getdate(self.job_end_date)
			if job_end > fy_end:
				frappe.throw(f"Job End Date cannot exceed fiscal year end ({fy_end}). Create a new job for the next fiscal year.")
			if job_end < fy_start:
				frappe.throw(f"Job End Date cannot be before fiscal year start ({fy_start})")
	
	def validate_job_dates(self):
		"""Validate job date logic"""
		if self.job_start_date and self.job_end_date:
			if getdate(self.job_end_date) < getdate(self.job_start_date):
				frappe.throw("Job End Date cannot be before Job Start Date")
	
	def calculate_job_validity(self):
		"""Calculate job validity in days"""
		if self.job_start_date and self.job_end_date:
			self.job_validity_days = date_diff(self.job_end_date, self.job_start_date) + 1
	
	def before_submit(self):
		"""Actions before submit"""
		if self.status == "Draft":
			self.status = "Active"
		
		# Lock validity dates on submit
		if not self.allow_validity_override:
			self.db_set('allow_validity_override', 0)
	
	def on_submit(self):
		"""Actions on submit"""
		pass
	
	def calculate_storage_days(self):
		"""Calculate total storage days"""
		if self.storage_start_date and self.storage_end_date:
			self.total_storage_days = date_diff(self.storage_end_date, self.storage_start_date) + 1
		elif self.storage_start_date:
			self.total_storage_days = date_diff(today(), self.storage_start_date) + 1
	
	def calculate_storage_charges(self):
		"""Calculate storage charge amounts based on period and rates"""
		for charge in self.storage_charges:
			# Calculate storage days
			if charge.start_date and charge.end_date:
				charge.storage_days = date_diff(charge.end_date, charge.start_date) + 1
			elif charge.start_date:
				charge.storage_days = date_diff(today(), charge.start_date) + 1
			else:
				charge.storage_days = 0
			
			# Get rate for this UOM from storage_rate_item table
			rate_per_day = 0
			min_days = 0
			
			for rate_item in self.storage_rate_item:
				if rate_item.uom == charge.uom:
					rate_per_day = flt(rate_item.rate_per_day)
					min_days = flt(rate_item.minimum_charge_days)
					break
			
			# Apply minimum charge days
			chargeable_days = max(charge.storage_days, min_days)
			
			# Calculate amount: Quantity × Days × Rate per Day
			charge.amount = flt(charge.quantity) * chargeable_days * rate_per_day
	
	def calculate_handling_charges(self):
		"""Calculate handling charge amounts"""
		for charge in self.handling_charges:
			charge.amount = flt(charge.quantity) * flt(charge.rate)
	
	def calculate_totals(self):
		"""Calculate total charges"""
		self.total_storage_charges = sum(flt(d.amount) for d in self.storage_charges)
		self.total_handling_charges = sum(flt(d.amount) for d in self.handling_charges)
		self.total_charges = self.total_storage_charges + self.total_handling_charges
		
		# Calculate invoiced and pending amounts
		self.invoiced_amount = sum(flt(d.amount) for d in self.storage_charges if d.is_invoiced)
		self.invoiced_amount += sum(flt(d.amount) for d in self.handling_charges if d.is_invoiced)
		self.pending_amount = self.total_charges - self.invoiced_amount
	
	def validate_invoiced_rows(self):
		"""Prevent editing invoiced rows"""
		if not self.is_new():
			old_doc = self.get_doc_before_save()
			if old_doc:
				# Check storage charges
				for idx, charge in enumerate(self.storage_charges):
					if idx < len(old_doc.storage_charges):
						old_charge = old_doc.storage_charges[idx]
						if old_charge.is_invoiced and (
							charge.quantity != old_charge.quantity or
							charge.rate_per_day != old_charge.rate_per_day or
							charge.rate_per_month != old_charge.rate_per_month
						):
							frappe.throw(f"Row {charge.idx} in Storage Charges is already invoiced and cannot be modified")
				
				# Check handling charges
				for idx, charge in enumerate(self.handling_charges):
					if idx < len(old_doc.handling_charges):
						old_charge = old_doc.handling_charges[idx]
						if old_charge.is_invoiced and (
							charge.quantity != old_charge.quantity or
							charge.rate != old_charge.rate
						):
							frappe.throw(f"Row {charge.idx} in Handling Charges is already invoiced and cannot be modified")
	
	@frappe.whitelist()
	def load_handling_logs(self):
		"""Load handling charges from Handling Service Logs"""
		# Get all handling logs for this job
		logs = frappe.get_all("Handling Service Log", {
			"warehouse_job": self.name,
			"docstatus": 1
		}, ["name"])
		
		for log_name in logs:
			log = frappe.get_doc("Handling Service Log", log_name["name"])
			
			# Check if already added
			existing = [d for d in self.handling_charges if d.get("handling_service_log") == log.name]
			if existing:
				continue
			
			# Get activity details
			activity = frappe.get_doc("Handling Activity Type", log.activity_type)
			
			for item in log.items:
				self.append("handling_charges", {
					"activity_date": getdate(log.log_date),
					"handling_activity_type": log.activity_type,
					"description": item.description,
					"quantity": item.quantity,
					"uom": item.uom,
					"rate": item.rate,
					"amount": item.amount
				})
		
		self.calculate_handling_charges()
		self.calculate_totals()
		frappe.msgprint("Handling charges loaded from service logs")
	
	@frappe.whitelist()
	def calculate_current_storage_charges(self):
		"""Auto-calculate storage charges from receipt items"""
		if not self.goods_receipt:
			frappe.throw("Please select a Goods Receipt")
		
		receipt = frappe.get_doc("Customer Goods Receipt", self.goods_receipt)
		
		# Get applicable rate card
		from freightmas.warehouse_service.doctype.storage_rate_card.storage_rate_card import StorageRateCard
		rate_card_name = StorageRateCard.get_applicable_rate_card(self.customer, self.storage_start_date)
		
		if not rate_card_name:
			frappe.msgprint("No applicable rate card found. Please enter rates manually.")
			return
		
		rate_card = frappe.get_doc("Storage Rate Card", rate_card_name)
		
		# Clear existing storage charges
		self.storage_charges = []
		
		for item in receipt.items:
			if flt(item.quantity_remaining) <= 0:
				continue
			
			# Find matching rate by storage unit type
			rate_item = None
			for rate in rate_card.rate_items:
				if rate.storage_unit_type == item.storage_unit_type:
					rate_item = rate
					break
			
			if not rate_item:
				continue
			
			self.append("storage_charges", {
				"goods_receipt_item": item.name,
				"storage_unit_type": item.storage_unit_type,
				"quantity": item.quantity_remaining,
				"start_date": self.storage_start_date or receipt.receipt_date,
				"end_date": self.storage_end_date,
				"rate_per_day": rate_item.rate_per_day,
				"rate_per_month": rate_item.rate_per_month,
				"rate_type": "Per Day" if rate_item.rate_per_day else "Per Month",
				"free_days": rate_item.free_days or 0
			})
		
		self.calculate_storage_charges()
		self.calculate_totals()
		frappe.msgprint(f"Storage charges calculated using rate card: {rate_card_name}")
	
	@frappe.whitelist()
	def create_sales_invoice(self, charges_to_invoice=None):
		"""Create Sales Invoice from selected charges"""
		if not charges_to_invoice:
			frappe.throw("Please select charges to invoice")
		
		import json
		if isinstance(charges_to_invoice, str):
			charges_to_invoice = json.loads(charges_to_invoice)
		
		# Create Sales Invoice
		si = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": self.customer,
			"posting_date": today(),
			"due_date": today(),
			"warehouse_job": self.name,
			"items": []
		})
		
		# Add storage charges
		for charge_name in charges_to_invoice.get("storage_charges", []):
			charge = frappe.get_doc("Warehouse Job Storage Charges", charge_name)
			if not charge.is_invoiced:
				si.append("items", {
					"item_code": "WMS-STORAGE",  # Create this service item
					"item_name": "Warehouse Storage Service",
					"description": f"Storage for {charge.quantity} {charge.storage_unit_type} ({charge.chargeable_days} days)",
					"qty": 1,
					"rate": charge.amount,
					"amount": charge.amount
				})
		
		# Add handling charges
		for charge_name in charges_to_invoice.get("handling_charges", []):
			charge = frappe.get_doc("Warehouse Job Handling Charges", charge_name)
			if not charge.is_invoiced:
				si.append("items", {
					"item_code": "WMS-HANDLING",  # Create this service item
					"item_name": "Warehouse Handling Service",
					"description": f"{charge.description} ({charge.quantity} {charge.uom})",
					"qty": 1,
					"rate": charge.amount,
					"amount": charge.amount
				})
		
		si.insert(ignore_permissions=True)
		
		# Mark charges as invoiced
		for charge_name in charges_to_invoice.get("storage_charges", []):
			frappe.db.set_value("Warehouse Job Storage Charges", charge_name, {
				"is_invoiced": 1,
				"sales_invoice": si.name
			})
		
		for charge_name in charges_to_invoice.get("handling_charges", []):
			frappe.db.set_value("Warehouse Job Handling Charges", charge_name, {
				"is_invoiced": 1,
				"sales_invoice": si.name
			})
		
		self.reload()
		self.calculate_totals()
		self.save()
		
		frappe.msgprint(f"Sales Invoice {si.name} created successfully")
		return si.name
	
	@frappe.whitelist()
	def get_transactions_html(self):
		"""Generate HTML for transactions tab"""
		receipts = frappe.db.sql("""
			SELECT 
				name,
				receipt_date,
				reference_number,
				vehicle_number,
				docstatus,
				CASE 
					WHEN docstatus = 0 THEN 'Draft'
					WHEN docstatus = 1 THEN 'Submitted'
					WHEN docstatus = 2 THEN 'Cancelled'
				END as status,
				(SELECT COUNT(*) FROM `tabCustomer Goods Receipt Item` 
				 WHERE parent = `tabCustomer Goods Receipt`.name) as item_count,
				(SELECT SUM(quantity) FROM `tabCustomer Goods Receipt Item` 
				 WHERE parent = `tabCustomer Goods Receipt`.name) as total_quantity
			FROM `tabCustomer Goods Receipt`
			WHERE warehouse_job = %(job)s
			AND docstatus != 2
			ORDER BY receipt_date DESC, creation DESC
		""", {"job": self.name}, as_dict=1)
		
		# Get dispatches
		dispatches = frappe.db.sql("""
			SELECT 
				name,
				dispatch_date,
				reference_number,
				vehicle_number,
				docstatus,
				CASE 
					WHEN docstatus = 0 THEN 'Draft'
					WHEN docstatus = 1 THEN 'Submitted'
					WHEN docstatus = 2 THEN 'Cancelled'
				END as status,
				(SELECT COUNT(*) FROM `tabCustomer Goods Dispatch Item` 
				 WHERE parent = `tabCustomer Goods Dispatch`.name) as item_count,
				(SELECT SUM(quantity) FROM `tabCustomer Goods Dispatch Item` 
				 WHERE parent = `tabCustomer Goods Dispatch`.name) as total_quantity
			FROM `tabCustomer Goods Dispatch`
			WHERE warehouse_job = %(job)s
			AND docstatus != 2
			ORDER BY dispatch_date DESC, creation DESC
		""", {"job": self.name}, as_dict=1)
		
		# Calculate stock balance by combining receipts and dispatches
		stock_balance = frappe.db.sql("""
			SELECT 
				COALESCE(storage_unit_type, 'N/A') as storage_unit_type,
				COALESCE(warehouse_bay, 'Unassigned') as warehouse_bay,
				SUM(total_received) as total_received,
				SUM(total_dispatched) as total_dispatched,
				SUM(total_received) - SUM(total_dispatched) as current_balance,
				COUNT(DISTINCT bin_name) as bin_count
			FROM (
				-- Receipts
				SELECT 
					gri.storage_unit_type,
					gri.warehouse_bay,
					SUM(gri.quantity) as total_received,
					0 as total_dispatched,
					gri.warehouse_bin as bin_name
				FROM `tabCustomer Goods Receipt Item` gri
				INNER JOIN `tabCustomer Goods Receipt` gr ON gr.name = gri.parent
				WHERE gr.warehouse_job = %(job)s
				AND gr.docstatus = 1
				GROUP BY gri.storage_unit_type, gri.warehouse_bay, gri.warehouse_bin
				
				UNION ALL
				
				-- Dispatches
				SELECT 
					gdi.storage_unit_type,
					gdi.warehouse_bay,
					0 as total_received,
					SUM(gdi.quantity) as total_dispatched,
					NULL as bin_name
				FROM `tabCustomer Goods Dispatch Item` gdi
				INNER JOIN `tabCustomer Goods Dispatch` gd ON gd.name = gdi.parent
				WHERE gd.warehouse_job = %(job)s
				AND gd.docstatus = 1
				GROUP BY gdi.storage_unit_type, gdi.warehouse_bay
			) combined
			GROUP BY storage_unit_type, warehouse_bay
			ORDER BY storage_unit_type, warehouse_bay
		""", {"job": self.name}, as_dict=1)
		
		return frappe.render_template(
			"freightmas/warehouse_service/doctype/warehouse_job/warehouse_job_transactions.html",
			{
				"doc": self,
				"receipts": receipts,
				"dispatches": dispatches,
				"stock_balance": stock_balance
			}
		)
	
	@frappe.whitelist()
	def fetch_handling_charges(self):
		"""Fetch handling charges from submitted receipts and dispatches"""
		# Get all submitted receipts for this job
		receipts = frappe.get_all(
			"Customer Goods Receipt",
			filters={
				"warehouse_job": self.name,
				"docstatus": 1
			},
			fields=["name", "receipt_date", "customer"]
		)
		
		# Get all submitted dispatches for this job
		dispatches = frappe.get_all(
			"Customer Goods Dispatch",
			filters={
				"warehouse_job": self.name,
				"docstatus": 1
			},
			fields=["name", "dispatch_date", "customer"]
		)
		
		# Track existing charges to avoid duplicates
		existing_charges = set()
		for charge in self.handling_charges:
			if charge.source_document and charge.source_item:
				existing_charges.add((charge.source_document, charge.source_item))
		
		charges_added = 0
		
		# Fetch charges from receipts
		for receipt in receipts:
			receipt_doc = frappe.get_doc("Customer Goods Receipt", receipt.name)
			
			for charge_row in receipt_doc.handling_charges:
				# Check if this charge already exists
				key = (receipt.name, charge_row.name)
				if key in existing_charges:
					continue
				
				# Add new charge row
				self.append("handling_charges", {
					"activity_date": receipt.receipt_date,
					"handling_activity_type": charge_row.handling_service_type,
					"description": f"{charge_row.service_category or ''} - {charge_row.remarks or ''}".strip(" -"),
					"quantity": charge_row.quantity,
					"uom": self.map_unit_to_uom(charge_row.unit),
					"rate": charge_row.rate,
					"amount": charge_row.amount,
					"customer": receipt.customer,
					"source_document_type": "Customer Goods Receipt",
					"source_document": receipt.name,
					"source_item": charge_row.name
				})
				charges_added += 1
		
		# Fetch charges from dispatches
		for dispatch in dispatches:
			dispatch_doc = frappe.get_doc("Customer Goods Dispatch", dispatch.name)
			
			for charge_row in dispatch_doc.handling_charges:
				# Check if this charge already exists
				key = (dispatch.name, charge_row.name)
				if key in existing_charges:
					continue
				
				# Add new charge row
				self.append("handling_charges", {
					"activity_date": dispatch.dispatch_date,
					"handling_activity_type": charge_row.handling_service_type,
					"description": f"{charge_row.service_category or ''} - {charge_row.remarks or ''}".strip(" -"),
					"quantity": charge_row.quantity,
					"uom": self.map_unit_to_uom(charge_row.unit),
					"rate": charge_row.rate,
					"amount": charge_row.amount,
					"customer": dispatch.customer,
					"source_document_type": "Customer Goods Dispatch",
					"source_document": dispatch.name,
					"source_item": charge_row.name
				})
				charges_added += 1
		
		# Recalculate totals
		self.calculate_handling_charges()
		self.calculate_totals()
		
		return {
			"message": f"Added {charges_added} handling charge(s)",
			"charges_added": charges_added
		}
	
	def map_unit_to_uom(self, unit):
		"""Map receipt/dispatch unit to warehouse job UOM"""
		mapping = {
			"Per Pallet": "Pallets",
			"Per CBM": "Fixed",
			"Per Ton": "Fixed",
			"Per Unit": "Cartons",
			"Per Hour": "Hours",
			"Flat Rate": "Fixed"
		}
		return mapping.get(unit, "Fixed")


@frappe.whitelist()
def create_sales_invoice_with_rows(docname, row_names):
	"""Create Sales Invoice from selected handling and storage charges"""
	import json
	from frappe.utils import nowdate
	
	row_data = json.loads(row_names)
	job = frappe.get_doc("Warehouse Job", docname)
	
	# Separate handling and storage charges
	handling_names = [r['name'] for r in row_data if r.get('charge_type') == 'Handling']
	storage_names = [r['name'] for r in row_data if r.get('charge_type') == 'Storage']
	
	selected_handling = [row for row in job.handling_charges if row.name in handling_names]
	selected_storage = [row for row in job.storage_charges if row.name in storage_names]
	
	if not selected_handling and not selected_storage:
		frappe.throw("No valid charges selected.")
	
	# Create Sales Invoice
	si = frappe.new_doc("Sales Invoice")
	# Use customer from handling charges if available, otherwise use job customer
	si.customer = selected_handling[0].customer if selected_handling else job.customer
	si.set_posting_time = 1
	si.posting_date = nowdate()
	
	# Add reference to warehouse job
	try:
		if si.meta.get_field("warehouse_job_reference"):
			si.warehouse_job_reference = job.name
	except Exception:
		pass
	
	# Generate remarks
	handling_count = len(selected_handling)
	storage_count = len(selected_storage)
	remarks_parts = []
	if handling_count:
		remarks_parts.append(f"{handling_count} handling charge(s)")
	if storage_count:
		remarks_parts.append(f"{storage_count} storage charge(s)")
	si.remarks = f"Warehouse Job {job.name}: {', '.join(remarks_parts)}"
	
	# Add handling charge items
	for row in selected_handling:
		si.append("items", {
			"item_code": row.handling_activity_type or "Handling Service",
			"description": row.description or row.handling_activity_type or "Handling Service",
			"qty": row.quantity or 1,
			"rate": row.rate or 0,
			"amount": row.amount or 0
		})
	
	# Add storage charge items
	for row in selected_storage:
		si.append("items", {
			"item_code": "Storage Service",
			"description": f"Storage: {row.uom} - {row.storage_days} days ({row.start_date} to {row.end_date})",
			"qty": row.quantity or 1,
			"rate": row.amount / row.quantity if row.quantity else row.amount,
			"amount": row.amount or 0
		})
	
	# Save and return
	si.insert()
	
	# Update handling charges with invoice reference
	for row in selected_handling:
		frappe.db.set_value("Warehouse Job Handling Charges", row.name, {
			"sales_invoice": si.name,
			"is_invoiced": 1
		})
	
	# Update storage charges with invoice reference
	for row in selected_storage:
		frappe.db.set_value("Warehouse Job Storage Charges", row.name, {
			"is_invoiced": 1
		})
	
	# Reload job to update invoiced amount
	job.reload()
	
	return si.name


@frappe.whitelist()
def calculate_monthly_storage_for_job(docname, start_date, end_date):
	"""
	Calculate storage charges for a job for a given period.
	Groups consecutive days with same UOM quantities into charge periods.
	Only calculates up to today, skips already charged periods.
	
	Args:
		docname: Warehouse Job name
		start_date: Period start date (YYYY-MM-DD)
		end_date: Period end date (YYYY-MM-DD)
	"""
	job = frappe.get_doc("Warehouse Job", docname)
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	today_date = getdate(today())
	
	# Don't calculate into the future - limit end_date to today
	if end_date > today_date:
		end_date = today_date
	
	# Validate storage rates are defined
	if not job.storage_rate_item:
		frappe.throw("Storage rates not defined in Storage Rate Item table")
	
	# Get existing charged periods to avoid duplicates
	# Check all existing charges (both invoiced and uninvoiced)
	existing_charges = {}
	for charge in job.storage_charges:
		uom = charge.uom
		if uom not in existing_charges:
			existing_charges[uom] = []
		existing_charges[uom].append((getdate(charge.start_date), getdate(charge.end_date)))
	
	# Get all receipts for this job
	receipts = frappe.get_all(
		"Customer Goods Receipt",
		filters={"warehouse_job": docname, "docstatus": 1},
		fields=["name", "receipt_date"]
	)
	
	if not receipts:
		frappe.msgprint("No receipts found for this job")
		return
	
	# Build daily inventory snapshots
	# Structure: {date: {uom: quantity}}
	daily_inventory = {}
	
	current_date = start_date
	while current_date <= end_date:
		daily_inventory[current_date] = {}
		current_date = frappe.utils.add_days(current_date, 1)
	
	# For each receipt item, calculate quantity in warehouse for each day
	for receipt in receipts:
		items = frappe.get_all(
			"Customer Goods Receipt Item",
			filters={"parent": receipt.name},
			fields=["name", "uom", "quantity", "quantity_remaining"]
		)
		
		receipt_date = getdate(receipt.receipt_date) if receipt.receipt_date else start_date
		
		for item in items:
			# Add to daily inventory for each day in period
			for day in daily_inventory:
				if day >= receipt_date:
					uom = item.uom
					qty = flt(item.quantity_remaining)
					
					if qty > 0:
						if uom not in daily_inventory[day]:
							daily_inventory[day][uom] = 0
						daily_inventory[day][uom] += qty
	
	# Group consecutive days with same UOM quantities into charge periods
	# Structure: {uom: [(start_date, end_date, quantity)]}
	charge_periods = {}
	
	for uom_rate in job.storage_rate_item:
		uom = uom_rate.uom
		charge_periods[uom] = []
		
		period_start = None
		period_qty = 0
		
		for day in sorted(daily_inventory.keys()):
			current_qty = daily_inventory[day].get(uom, 0)
			
			# Check if this day is already charged (invoiced)
			day_already_charged = False
			if uom in existing_charges:
				for charged_start, charged_end in existing_charges[uom]:
					if charged_start <= day <= charged_end:
						day_already_charged = True
						break
			
			if day_already_charged:
				# Close any open period before this charged day
				if period_start is not None:
					charge_periods[uom].append((period_start, frappe.utils.add_days(day, -1), period_qty))
					period_start = None
					period_qty = 0
				continue
			
			if current_qty > 0:
				if period_start is None:
					# Start new period
					period_start = day
					period_qty = current_qty
				elif current_qty != period_qty:
					# Quantity changed - close current period and start new one
					charge_periods[uom].append((period_start, frappe.utils.add_days(day, -1), period_qty))
					period_start = day
					period_qty = current_qty
			else:
				# No inventory for this UOM on this day
				if period_start is not None:
					# Close current period
					charge_periods[uom].append((period_start, frappe.utils.add_days(day, -1), period_qty))
					period_start = None
					period_qty = 0
		
		# Close any open period at end date
		if period_start is not None:
			charge_periods[uom].append((period_start, end_date, period_qty))
	
	# Create storage charge rows
	new_charges_count = 0
	for uom, periods in charge_periods.items():
		for period_start, period_end, qty in periods:
			if qty > 0:
				# Calculate days
				storage_days = date_diff(period_end, period_start) + 1
				
				# Get rate and minimum days
				rate_per_day = 0
				min_days = 0
				for rate_item in job.storage_rate_item:
					if rate_item.uom == uom:
						rate_per_day = flt(rate_item.rate_per_day)
						min_days = flt(rate_item.minimum_charge_days)
						break
				
				# Apply minimum charge days
				chargeable_days = max(storage_days, min_days)
				
				# Calculate amount
				amount = qty * chargeable_days * rate_per_day
				
				# Add charge row
				job.append("storage_charges", {
					"uom": uom,
					"quantity": qty,
					"start_date": period_start,
					"end_date": period_end,
					"storage_days": storage_days,
					"amount": amount,
					"is_invoiced": 0
				})
				new_charges_count += 1
	
	# Save job
	if new_charges_count > 0:
		job.save()
		frappe.msgprint(f"{new_charges_count} storage charge(s) created for period {start_date} to {end_date}")
	else:
		frappe.msgprint(f"No new charges to create. Period {start_date} to {end_date} already charged or no inventory.")
	
	return True


def calculate_all_monthly_storage():
	"""
	Scheduled task to calculate storage charges for all active warehouse jobs.
	Runs monthly to calculate previous month's storage charges.
	"""
	from frappe.utils import add_months, get_first_day, get_last_day
	
	# Calculate for previous month
	today_date = getdate(today())
	prev_month = add_months(today_date, -1)
	start_date = get_first_day(prev_month)
	end_date = get_last_day(prev_month)
	
	# Get all active warehouse jobs
	jobs = frappe.get_all(
		"Warehouse Job",
		filters={"status": "Active", "docstatus": 1},
		fields=["name"]
	)
	
	if not jobs:
		frappe.logger().info("No active warehouse jobs found for storage calculation")
		return
	
	success_count = 0
	error_count = 0
	
	for job in jobs:
		try:
			calculate_monthly_storage_for_job(job.name, start_date, end_date)
			success_count += 1
		except Exception as e:
			error_count += 1
			frappe.logger().error(f"Error calculating storage for job {job.name}: {str(e)}")
	
	frappe.logger().info(f"Monthly storage calculation completed. Success: {success_count}, Errors: {error_count}")
