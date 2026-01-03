# Storage Charges Implementation Guide

## Overview
Storage charges are calculated based on daily warehouse inventory snapshots, grouped by UOM (Unit of Measure). The system tracks how long goods remain in the warehouse and applies rates defined directly in the Warehouse Job.

## Doctype Structure

### Storage Rate Item (Child Table in Warehouse Job)
Defines storage rates per UOM for the job:
- **UOM**: Unit of measure (Pallet, Carton, etc.) - unique per job
- **Rate Per Day**: Daily storage rate for this UOM
- **Minimum Charge Days**: Minimum days to charge (e.g., minimum 3 days even if stored for 1 day)

### Warehouse Job Storage Charges (Child Table)
Stores calculated storage charge periods:
- **UOM**: Unit of measure
- **Quantity**: Number of units stored
- **Start Date**: Period start date
- **End Date**: Period end date
- **Storage Days**: Number of days stored
- **Amount**: Total charge amount
- **Is Invoiced**: Whether charge has been invoiced

## Calculation Logic

### Period-Based Grouping
The system groups consecutive days with the same UOM quantity into charge periods:

**Example:**
```
Storage Rates:
- Pallet: $36/day (min 3 days)
- Carton: $5/day (min 1 day)

Daily Inventory:
Jan 1-5:   10 Pallets, 50 Cartons
Jan 6-10:   6 Pallets, 50 Cartons
Jan 11-15:  6 Pallets, 30 Cartons

Charge Rows Created:
- Pallet, Qty 10, Jan 1-5, 5 days, $1,800
- Pallet, Qty 6, Jan 6-15, 10 days, $2,160
- Carton, Qty 50, Jan 1-10, 10 days, $2,500
- Carton, Qty 30, Jan 11-15, 5 days, $750
```

### Calculation Formula
```python
chargeable_days = max(storage_days, minimum_charge_days)
amount = quantity × chargeable_days × rate_per_day
```

## Usage

### Manual Calculation
1. Open a Warehouse Job
2. Ensure Storage Rate Item table is filled with rates
3. Click **Actions → Calculate Storage Charges**
4. Select date range (defaults to current month)
5. Click **Calculate**

System will:
- Get all receipts for the job
- Build daily inventory snapshots using `quantity_remaining` from receipt items
- Group consecutive days with same UOM quantities
- Create charge rows applying minimum charge days
- Save charges to Storage Charges table

### Automatic Monthly Calculation
A scheduled task runs on the 1st of each month to calculate previous month's charges for all active jobs:

**Scheduler Configuration** (hooks.py):
```python
scheduler_events = {
    "monthly": [
        "freightmas.warehouse_service.doctype.warehouse_job.warehouse_job.calculate_all_monthly_storage"
    ],
}
```

## Functions

### `calculate_storage_charges(self)`
Called during validation to calculate amounts for existing charge rows:
- Calculates storage days from start/end dates
- Gets rate from Storage Rate Item table by UOM
- Applies minimum charge days
- Calculates amount

### `calculate_monthly_storage_for_job(docname, start_date, end_date)`
Main calculation function (whitelisted for client calls):
1. Validates storage rates are defined
2. Gets all receipts for the job
3. Builds daily inventory snapshots:
   - For each day in period
   - For each receipt item
   - Tracks `quantity_remaining` by UOM
4. Groups consecutive days with same quantities into periods
5. Creates charge rows with calculated amounts

### `calculate_all_monthly_storage()`
Scheduled task that:
- Calculates for previous month (1st to last day)
- Processes all active warehouse jobs
- Logs success/error counts

## Data Flow

```
Customer Goods Receipt
  ↓ (receipt_date, uom, quantity_remaining)
Daily Inventory Snapshot
  ↓ (group by UOM, track quantities)
Charge Periods
  ↓ (consecutive days with same qty)
Warehouse Job Storage Charges
  ↓ (apply rates and minimum days)
Sales Invoice
```

## Key Features

1. **UOM-Based Calculation**: Different goods types (pallets, cartons, etc.) charged at different rates
2. **Period Grouping**: Efficient charge rows by grouping stable inventory periods
3. **Minimum Charge Days**: Ensures minimum charges (e.g., 3-day minimum for pallets)
4. **Quantity Tracking**: Uses `quantity_remaining` to track what's actually in warehouse
5. **Flexible Periods**: Manual calculation for any date range
6. **Automatic Monthly**: Scheduled task for hands-free operation

## Important Notes

- Storage rates are job-specific (not global)
- Each UOM can only appear once per job in Storage Rate Item
- Calculation is based on `quantity_remaining` from receipt items
- Charges are only created for days with inventory > 0
- Minimum charge days prevent under-charging for short-term storage
- System tracks dispatch dates to stop charging when goods leave warehouse
