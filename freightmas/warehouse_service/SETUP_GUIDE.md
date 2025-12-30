# Warehouse Service Module - Quick Setup Guide

## 🚀 Installation & Setup

### Step 1: Install the Module

The module files have been created. Now you need to install them in your Frappe/ERPNext instance.

```bash
cd /home/simbarashe/frappe-bench

# Migrate the database to create new doctypes
bench --site [your-site-name] migrate

# Clear cache
bench --site [your-site-name] clear-cache

# Restart bench
bench restart
```

### Step 2: Create Service Items

Navigate to: **Item** → **New Item**

Create these two service items:

#### 1. WMS-STORAGE
- **Item Code:** WMS-STORAGE
- **Item Name:** Warehouse Storage Service
- **Item Group:** Services
- **Is Stock Item:** ❌ No (CRITICAL)
- **Is Service Item:** ✅ Yes

#### 2. WMS-HANDLING  
- **Item Code:** WMS-HANDLING
- **Item Name:** Warehouse Handling Service
- **Item Group:** Services
- **Is Stock Item:** ❌ No (CRITICAL)
- **Is Service Item:** ✅ Yes

### Step 3: Setup Basic Data

#### Create Warehouse Zones
Navigate to: **Warehouse Service** → **Warehouse Zone**

Example zones:
```
Code: ZONE-A
Name: Zone A - Ambient Storage
Type: Ambient
Total Area (SQM): 500
```

```
Code: ZONE-B
Name: Zone B - Cold Storage
Type: Cold Storage
Total Area (SQM): 300
```

#### Create Warehouse Bays
Navigate to: **Warehouse Service** → **Warehouse Bay**

Example bays:
```
Zone: ZONE-A
Bay Code: A-01
Bay Type: Pallet Racking
Capacity (Pallets): 50
```

```
Zone: ZONE-A
Bay Code: A-02
Bay Type: Floor Storage
Capacity (SQM): 100
```

#### Create Warehouse Bins
Navigate to: **Warehouse Service** → **Warehouse Bin**

Example bins (create multiple):
```
Zone: ZONE-A
Bay: A-01
Bin Code: A-01-01
Bin Type: Pallet Position
Max Weight (KG): 1000
```

```
Zone: ZONE-A
Bay: A-01
Bin Code: A-01-02
Bin Type: Pallet Position
Max Weight (KG): 1000
```

#### Create Storage Unit Types
Navigate to: **Warehouse Service** → **Storage Unit Type**

Example types:
```
Unit Type: Euro Pallet
Length: 120 cm
Width: 80 cm
Height: 150 cm
Default Rate Per Day: $5.00
Default Rate Per Month: $120.00
```

```
Unit Type: IBC Container
Length: 100 cm
Width: 100 cm
Height: 120 cm
Default Rate Per Day: $8.00
Default Rate Per Month: $200.00
```

#### Create Handling Activity Types
Navigate to: **Warehouse Service** → **Handling Activity Type**

Example activities:
```
Activity Code: OFFLOAD
Activity Name: Offloading - Container
Category: Inbound
Default Rate: $150.00
Unit of Measure: Per Container
```

```
Activity Code: LOAD
Activity Name: Loading - Truck
Category: Outbound
Default Rate: $100.00
Unit of Measure: Per Truck
```

```
Activity Code: LABEL
Activity Name: Labelling Service
Category: Value-Added
Default Rate: $2.00
Unit of Measure: Per Carton
```

#### Create Storage Rate Card
Navigate to: **Warehouse Service** → **Storage Rate Card**

Example rate card:
```
Rate Card Name: Standard Rates 2025
Customer: (leave blank for general rates)
Valid From: 2025-01-01
Currency: USD
Is Default: ✅ Yes

Rate Items:
Row 1:
  Storage Unit Type: Euro Pallet
  Zone Type: Ambient
  Rate Per Day: $5.00
  Rate Per Month: $120.00
  Free Days: 0

Row 2:
  Storage Unit Type: Euro Pallet
  Zone Type: Cold Storage
  Rate Per Day: $8.00
  Rate Per Month: $200.00
  Free Days: 0

Row 3:
  Storage Unit Type: IBC Container
  Zone Type: Ambient
  Rate Per Day: $8.00
  Rate Per Month: $200.00
  Free Days: 0
```

### Step 4: Test the System

#### Test 1: Create Goods Receipt

Navigate to: **Warehouse Service** → **Customer Goods Receipt**

```
Customer: [Select a customer]
Receipt Date: Today
Vehicle Number: ABC-1234
Driver Name: John Doe

Items:
Row 1:
  Customer Reference: CUST-SKU-001
  Description: Electronic Goods - Cartons
  Storage Unit Type: Euro Pallet
  Quantity: 10
  Weight (KG): 500
  Warehouse Zone: ZONE-A
  Warehouse Bay: A-01
  Warehouse Bin: A-01-01
```

Click **Save** → **Submit**

**Expected Results:**
- ✅ Bins marked as occupied
- ✅ Goods Movement record created
- ✅ Warehouse Job auto-created
- ✅ Handling Service Log created for offloading

#### Test 2: Create Warehouse Job Charges

Navigate to the auto-created Warehouse Job

Click **Calculate Current Storage Charges** button
- ✅ Storage charges populated automatically

Click **Load Handling Logs** button
- ✅ Handling charges populated from service logs

**Review charges:**
- Storage charges show days, chargeable days, amounts
- Handling charges show offloading activity

#### Test 3: Create Goods Dispatch

Navigate to: **Warehouse Service** → **Customer Goods Dispatch**

```
Customer: [Same customer as receipt]
Goods Receipt: [Select the receipt created above]
Dispatch Date: Today
Delivery Order Number: DO-001

Items:
Row 1:
  Goods Receipt Item: [Select from receipt]
  Quantity to Dispatch: 5 (out of 10)
```

Click **Save** → **Submit**

**Expected Results:**
- ✅ Quantity remaining updated (10 - 5 = 5)
- ✅ Goods Movement record created
- ✅ Handling Service Log created for loading
- ✅ Receipt status updated to "Partially Dispatched"

#### Test 4: Create Sales Invoice

Navigate back to the Warehouse Job

Click **Create Sales Invoice** (you'll need to implement UI for selecting rows)

**Expected Results:**
- ✅ Sales Invoice created with service items
- ✅ Selected rows marked as invoiced
- ✅ Cannot edit invoiced rows

### Step 5: View Reports

#### Customer Inventory Report
Navigate to: **Warehouse Service** → **Customer Inventory Report**

Should show:
- Current stock on hand for each customer
- Days in storage
- Location details

#### Goods Movement Register
Navigate to: **Warehouse Service** → **Goods Movement Register**

Should show:
- Complete audit trail of all movements
- Inbound, Outbound, Relocation activities

---

## ⚠️ Critical Reminders

### DO NOT:
- ❌ Create Stock Entry for customer goods
- ❌ Use Material Receipt for customer goods
- ❌ Use Delivery Note for customer goods
- ❌ Set "Is Stock Item" = Yes on service items
- ❌ Record customer goods in Stock Ledger

### DO:
- ✅ Use Customer Goods Receipt (custom)
- ✅ Use Customer Goods Dispatch (custom)
- ✅ Track via Goods Movement (custom)
- ✅ Bill via Sales Invoice with service items
- ✅ Keep customer goods separate from company inventory

---

## 🐛 Troubleshooting

### Issue: Doctypes not showing after migrate
**Solution:**
```bash
bench --site [site] clear-cache
bench restart
```

### Issue: Cannot create Goods Receipt
**Solution:**
- Ensure Warehouse Zones, Bays, Bins are created first
- Ensure Storage Unit Types exist
- Check user has proper role (Warehouse Manager/User)

### Issue: Storage charges not calculating
**Solution:**
- Ensure Storage Rate Card exists with "Is Default" checked
- Ensure rate items match storage unit types and zone types
- Check valid from/to dates on rate card

### Issue: Service items missing when creating invoice
**Solution:**
- Create WMS-STORAGE and WMS-HANDLING items
- Set "Is Stock Item" = No, "Is Service Item" = Yes
- Update item codes in warehouse_job.py if needed

---

## 📞 Next Steps

1. **Customize as needed:**
   - Add more zones, bays, bins
   - Define customer-specific rate cards
   - Add more handling activity types

2. **Enhance the system:**
   - Add custom print formats
   - Create dashboard charts
   - Setup email notifications
   - Add barcode scanning

3. **Train users:**
   - Warehouse operators for receipts/dispatches
   - Billing team for job management
   - Management for reports

---

## 📚 Documentation

Full documentation available in:
`/home/simbarashe/frappe-bench/apps/freightmas/freightmas/warehouse_service/README.md`

---

**Happy Warehousing! 📦🏭**
