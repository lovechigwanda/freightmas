# Warehouse Service Module

## Overview

The **Warehouse Service** module is a complete 3PL (Third-Party Logistics) Warehouse Management System (WMS) built on top of ERPNext/Frappe framework.

### ⚠️ CRITICAL BUSINESS RULES

1. **NO Stock Ledger Integration**: Customer goods are NEVER recorded in ERPNext Stock Ledger
2. **Custom Tracking Only**: All customer goods tracked via custom doctypes
3. **Service-Based Billing**: Revenue from storage & handling services only
4. **Client Goods Ownership**: Goods remain customer-owned at all times

---

## Module Structure

```
warehouse_service/
├── doctype/
│   ├── warehouse_zone/                    # Master: Physical warehouse areas
│   ├── warehouse_bay/                     # Master: Storage locations
│   ├── warehouse_bin/                     # Master: Specific bin positions
│   ├── storage_unit_type/                 # Master: Pallet, cage, box types
│   ├── handling_activity_type/            # Master: Types of handling services
│   ├── storage_rate_card/                 # Master: Pricing templates
│   ├── storage_rate_card_item/            # Child: Rate card items
│   ├── customer_goods_receipt/            # Transaction: Goods IN
│   ├── customer_goods_receipt_item/       # Child: Receipt items
│   ├── customer_goods_dispatch/           # Transaction: Goods OUT
│   ├── customer_goods_dispatch_item/      # Child: Dispatch items
│   ├── goods_movement/                    # Transaction: Movement audit trail
│   ├── goods_movement_item/               # Child: Movement items
│   ├── handling_service_log/              # Transaction: Services rendered
│   ├── handling_service_log_item/         # Child: Service details
│   ├── warehouse_job/                     # Transaction: Main billing job
│   ├── warehouse_job_storage_charges/     # Child: Storage billing
│   └── warehouse_job_handling_charges/    # Child: Handling billing
├── report/
│   ├── customer_inventory_report/         # Current stock by customer
│   └── goods_movement_register/           # Movement audit trail
├── workspace/
│   └── warehouse_service.json             # Workspace configuration
└── README.md (this file)
```

---

## Key Doctypes

### 1. Masters

#### Warehouse Zone
Physical warehouse areas (e.g., "Zone A - Ambient", "Zone B - Cold Storage")

**Key Fields:**
- Zone Code (unique identifier)
- Zone Name
- Zone Type (Ambient/Cold Storage/Hazmat/Open Yard)
- Total Area (SQM)

#### Warehouse Bay
Storage locations within zones

**Key Fields:**
- Zone (Link to Warehouse Zone)
- Bay Code (unique)
- Bay Type (Pallet Racking/Floor Storage/Mezzanine)
- Capacity (Pallets/SQM)

#### Warehouse Bin
Specific storage positions (e.g., "A-01-03" = Zone A, Bay 01, Position 03)

**Key Fields:**
- Zone, Bay
- Bin Code (unique)
- Is Occupied (auto-calculated)
- Current Customer (read-only)
- Current Goods Receipt (read-only)

#### Storage Rate Card
Pricing templates for storage services

**Key Fields:**
- Rate Card Name
- Customer (optional - for customer-specific rates)
- Valid From/To dates
- Rate Items (child table with rates per unit type)

---

### 2. Core Transactions

#### Customer Goods Receipt ⭐
**THE INBOUND DOCUMENT** - Records customer goods arriving at warehouse

**Key Fields:**
- Customer
- Receipt Date
- Vehicle Details (Transporter, Vehicle Number, Driver)
- Items (child table with storage locations)

**On Submit:**
1. Creates Goods Movement records (Inbound)
2. Updates Warehouse Bin occupancy
3. Creates or links to Warehouse Job
4. Auto-creates Handling Service Log for offloading

#### Customer Goods Dispatch ⭐
**THE OUTBOUND DOCUMENT** - Records customer goods leaving warehouse

**Key Fields:**
- Customer
- Goods Receipt (source)
- Dispatch Date
- Items to dispatch (child table)

**On Submit:**
1. Updates Customer Goods Receipt Item.quantity_remaining
2. Creates Goods Movement records (Outbound)
3. Releases Warehouse Bin if fully emptied
4. Auto-creates Handling Service Log for loading
5. Updates receipt status

#### Warehouse Job ⭐
**THE BILLING CENTER** - Main document for tracking and billing services

**Key Fields:**
- Customer
- Job Type (Storage Only/Handling Only/Storage + Handling)
- Storage Start/End Dates
- Storage Charges (child table)
- Handling Charges (child table)
- Total Charges

**Key Methods:**
- `calculate_current_storage_charges()` - Auto-calculate from receipt items
- `load_handling_logs()` - Load from Handling Service Logs
- `create_sales_invoice()` - Generate invoice from selected charges

---

## Workflow

### Standard Storage & Handling Process

```
1. Customer books storage space
   ↓
2. Create WAREHOUSE JOB (Draft)
   ↓
3. Goods arrive → Create CUSTOMER GOODS RECEIPT
   - Assign zones/bays/bins
   - Record quantities, dimensions
   - Link to Warehouse Job
   - System auto-creates Handling Service Log (Offloading)
   ↓
4. Submit Receipt
   - Creates Goods Movement (Inbound)
   - Marks bins as occupied
   ↓
5. Daily: System calculates storage days
   ↓
6. Customer requests dispatch
   - Create CUSTOMER GOODS DISPATCH
   - Select items from receipt
   - System auto-creates Handling Service Log (Loading)
   ↓
7. Submit Dispatch
   - Creates Goods Movement (Outbound)
   - Releases bins if fully emptied
   - Updates receipt status
   ↓
8. On Warehouse Job:
   - Review storage charges (auto-calculated)
   - Review handling charges (from logs)
   - Select rows to invoice
   - Click "Create Sales Invoice"
   ↓
9. Mark job as Completed/Invoiced
```

---

## Billing Process

### Storage Charges
- Auto-calculated based on:
  - Storage unit type (pallet, cage, etc.)
  - Zone type (ambient, cold, etc.)
  - Number of days stored
  - Applicable rate card
  - Free days (if any)

### Handling Charges
- Auto-created from Handling Service Logs
- Common activities:
  - Offloading (on receipt)
  - Loading (on dispatch)
  - Labelling
  - Inspection
  - Relocation

### Invoice Creation
1. Open Warehouse Job
2. Click "Calculate Current Storage Charges" to populate storage charges
3. Click "Load Handling Logs" to populate handling charges
4. Select rows to invoice
5. Click "Create Sales Invoice"
6. System creates Sales Invoice with service items
7. Selected rows marked as invoiced (cannot be edited)

---

## Reports

### Customer Inventory Report
Shows what each customer currently has in storage

**Filters:**
- Customer
- Warehouse Zone
- Date Range
- Status

**Columns:**
- Goods Receipt #
- Description
- Quantity In/Dispatched/Remaining
- Location (Zone/Bay/Bin)
- Days in Storage
- Status

### Goods Movement Register
Complete audit trail of all goods movements

**Filters:**
- Customer
- Movement Type
- Date Range
- Warehouse Zone

**Columns:**
- Movement Date
- Movement Type
- Source/Destination Locations
- Moved By
- Reason

---

## Configuration Steps

### 1. Setup Masters

#### Create Warehouse Zones
```
Example:
- ZONE-A | Zone A - Ambient | Ambient | 500 SQM
- ZONE-B | Zone B - Cold Storage | Cold Storage | 300 SQM
- ZONE-C | Zone C - Open Yard | Open Yard | 1000 SQM
```

#### Create Warehouse Bays
```
Example:
- A-01 | Pallet Racking | 50 Pallets
- A-02 | Floor Storage | 100 SQM
- B-01 | Cold Storage Racking | 30 Pallets
```

#### Create Warehouse Bins
```
Example:
- A-01-01 | Zone A | Bay 01 | Position 01
- A-01-02 | Zone A | Bay 01 | Position 02
- B-01-01 | Zone B | Bay 01 | Position 01
```

#### Create Storage Unit Types
```
Example:
- Euro Pallet | 120cm x 80cm x 150cm | $5/day
- IBC Container | 100cm x 100cm x 120cm | $8/day
- Carton Box | 40cm x 30cm x 30cm | $0.50/day
```

#### Create Handling Activity Types
```
Example:
- OFFLOAD | Offloading - Container | Inbound | $150 per container
- LOAD | Loading - Truck | Outbound | $100 per truck
- LABEL | Labelling | Value-Added | $2 per carton
- INSPECT | Quality Inspection | Value-Added | $50 per hour
```

#### Create Storage Rate Cards
```
Example Rate Card: "Standard Rates 2025"
- Euro Pallet | Ambient | $5/day | $120/month | 0 free days
- Euro Pallet | Cold Storage | $8/day | $200/month | 0 free days
- IBC Container | Hazmat | $12/day | $300/month | 0 free days
```

### 2. Create Service Items in ERPNext

Navigate to: **Item** → **New Item**

Create these service items:
1. **WMS-STORAGE** - Warehouse Storage Service
2. **WMS-HANDLING** - Warehouse Handling Service

For both:
- Set "Is Stock Item" = No
- Set "Item Group" = Services
- Leave valuation/stock fields empty

### 3. Setup Roles & Permissions

Create these roles (if not existing):
- **Warehouse Manager** - Full access
- **Warehouse User** - Limited access (no delete)

---

## Safety Features

### Accounting Safeguards

```python
# Customer Goods Receipt - NO Stock Entry created
def on_submit(self):
    # NO frappe.get_doc("Stock Entry")
    # NO make_stock_entry()
    # Only custom movement tracking
    self.create_goods_movement_records()  # Custom tracking
    self.update_bin_occupancy()           # Custom tracking
```

### Invoice Row Protection

```python
# Warehouse Job - Prevents editing invoiced rows
def validate_invoiced_rows(self):
    if charge.is_invoiced:
        frappe.throw("Row is already invoiced and cannot be modified")
```

### Quantity Validation

```python
# Customer Goods Dispatch - Validates available quantity
def validate_quantities(self):
    if dispatch_qty > available_qty:
        frappe.throw("Dispatch quantity exceeds available quantity")
```

---

## Naming Series

- **WMS-GRN-.YYYY.-** → Customer Goods Receipt
- **WMS-GDN-.YYYY.-** → Customer Goods Dispatch
- **WMS-JOB-.YYYY.-** → Warehouse Job
- **WMS-MOV-.YYYY.-** → Goods Movement
- **WMS-HSL-.YYYY.-** → Handling Service Log

---

## Future Enhancements

### Phase 2 Features (Optional)
- [ ] Warehouse Occupancy Dashboard
- [ ] Storage Billing Summary Report
- [ ] Customer Goods Aging Report
- [ ] Warehouse Job Profitability Report
- [ ] Print Formats (Goods Receipt Note, Dispatch Note)
- [ ] Scheduled jobs for daily storage calculation
- [ ] Email notifications for dispatch reminders
- [ ] Barcode scanning for bins/goods
- [ ] Mobile app for warehouse operations

---

## Developer Notes

### Custom Fields vs Stock Ledger

**DO NOT use:**
- `Stock Entry`
- `Material Receipt`
- `Delivery Note` (for customer goods)
- `Purchase Receipt` (for customer goods)
- Any valuation fields

**DO use:**
- `Customer Goods Receipt` (custom)
- `Customer Goods Dispatch` (custom)
- `Goods Movement` (custom audit trail)
- `Sales Invoice` (for service billing only)

### Testing Checklist

- [ ] Create Warehouse Zone, Bay, Bin
- [ ] Create Storage Unit Type
- [ ] Create Handling Activity Type
- [ ] Create Storage Rate Card
- [ ] Create Customer Goods Receipt → Submit
- [ ] Verify Bins marked as occupied
- [ ] Verify Goods Movement created
- [ ] Verify Warehouse Job auto-created
- [ ] Create Customer Goods Dispatch → Submit
- [ ] Verify Quantity Remaining updated
- [ ] Verify Bins released (if fully dispatched)
- [ ] Calculate Storage Charges on Warehouse Job
- [ ] Load Handling Logs on Warehouse Job
- [ ] Create Sales Invoice from Warehouse Job
- [ ] Verify rows marked as invoiced
- [ ] Run Customer Inventory Report
- [ ] Run Goods Movement Register

---

## Support & Documentation

For questions or issues:
1. Check this README
2. Review doctype JSON files for field definitions
3. Review Python controllers for business logic
4. Check Frappe documentation: https://frappeframework.com/docs

---

**Version:** 1.0.0  
**Created:** December 27, 2025  
**Module:** Warehouse Service  
**App:** FreightMas
