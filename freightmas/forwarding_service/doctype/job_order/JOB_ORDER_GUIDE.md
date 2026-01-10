# Job Order - Sales to Operations Handover

## Overview

The **Job Order** DocType bridges the gap between Quotation (Sales) and Forwarding Job (Operations), providing a formal handover process with proper documentation and audit trail.

## Workflow

```
Quotation (Accepted)
    ↓
[Sales: Create Job Order]
    ↓
Job Order (Draft) - Sales prepares operational details
    ↓
Job Order (Submitted) - Official handover to Operations
    ↓
[Operations: Create Forwarding Job]
    ↓
Forwarding Job (Active) - Operational execution
```

## Key Features

### 1. One-to-One Relationship
- Each Quotation can generate only ONE Job Order
- Each Job Order creates only ONE Forwarding Job
- Prevents duplicates and confusion

### 2. Read-Only Service Charges
- Items are copied exactly from Quotation
- Cannot be edited in Job Order
- Ensures what was quoted is what gets executed

### 3. Document Tracking
- Includes document checklist similar to Forwarding Job
- Operations can track document requirements early
- Prepares for smooth job execution

### 4. Handover Trail
- Records who prepared (Sales User)
- Records who received (Operations User)
- Timestamps all conversions
- Full audit trail

## How to Use

### Step 1: Accept Quotation
1. Navigate to a Quotation
2. Ensure it's in "Accepted" workflow state
3. Ensure `job_type` = "Forwarding"

### Step 2: Create Job Order (Sales Team)
1. On the Accepted Quotation, click **Create → Create Job Order**
2. The Job Order is created with:
   - All items copied from quotation (read-only)
   - Customer and basic details pre-filled
   - Service details from quotation

3. Fill in operational requirements:
   - **Requested Service Date**: When customer needs service
   - **Special Instructions**: Any special handling notes
   - **Is Trucking Required?**: Check if trucking is needed
   - **Is Customs Clearance Required?**: Check if clearing needed

4. Add documents to checklist:
   - Bill of Lading
   - Commercial Invoice
   - Packing List
   - Certificate of Origin
   - etc.

5. **Operations Assigned To**: Assign to Operations team member

6. **Submit** the Job Order (locks it for editing)

### Step 3: Create Forwarding Job (Operations Team)
1. Open the submitted Job Order
2. Review all details
3. Click **Create → Create Forwarding Job**
4. Confirm the conversion

5. The system will:
   - Create a new Forwarding Job
   - Copy all charges to `forwarding_costing_charges`
   - Copy document checklist
   - Link Job Order to Forwarding Job
   - Record conversion timestamp and user

6. You'll be prompted to open the new Forwarding Job

### Step 4: Execute Forwarding Job (Operations Team)
1. Open the newly created Forwarding Job
2. Continue with normal operations:
   - Add tracking updates
   - Manage documents
   - Create invoices
   - etc.

## Field Mapping

### Quotation → Job Order
| Quotation Field | Job Order Field | Editable? |
|----------------|-----------------|-----------|
| company | company | No (fetch) |
| customer_name | customer | No (fetch) |
| direction | direction | No (fetch) |
| shipment_mode | shipment_mode | No (fetch) |
| origin_port | origin_port | No (fetch) |
| destination_port | destination_port | No (fetch) |
| incoterms | incoterms | No (fetch) |
| cargo_description | cargo_description | No (fetch) |
| currency | currency | No (fetch) |
| items | items | No (read-only) |

### Job Order → Forwarding Job
| Job Order Field | Forwarding Job Field | Notes |
|----------------|---------------------|-------|
| company | company | Direct copy |
| customer | customer | Direct copy |
| customer_po_reference | customer_reference | Direct copy |
| direction | direction | Direct copy |
| shipment_mode | shipment_mode | Direct copy |
| origin_port | port_of_loading | Direct copy |
| destination_port | destination | Direct copy |
| cargo_description | cargo_description | Direct copy |
| currency | currency | Direct copy |
| is_trucking_required | is_trucking_required | Direct copy |
| items | forwarding_costing_charges | Mapped to charges |
| documents_checklist | documents_checklist | Direct copy |

## Permissions

| Role | Create | Read | Write | Submit | Cancel |
|------|--------|------|-------|--------|--------|
| Sales User | ✓ | ✓ | ✓ | ✓ | - |
| Sales Manager | ✓ | ✓ | ✓ | ✓ | ✓ |
| Operations User | - | ✓ | ✓ | - | - |
| Operations Manager | - | ✓ | ✓ | - | ✓ |

**Notes:**
- Sales creates and submits Job Orders
- Operations can read and write (add notes, create Forwarding Job)
- Operations cannot cancel (prevents removing audit trail)
- Sales Manager can cancel if needed

## Validations

### Preventing Errors
1. **Quotation must be Accepted**: Cannot create Job Order from Draft/Pending quotations
2. **Forwarding Only**: Only works with Forwarding-type quotations
3. **No Duplicates**: Cannot create multiple Job Orders from same Quotation
4. **Cannot Cancel After Conversion**: Once converted to Forwarding Job, Job Order cannot be cancelled

### Data Integrity
1. Items are read-only (prevents modifications)
2. Service details fetched from Quotation (prevents data entry errors)
3. Links maintained throughout (Quotation ↔ Job Order ↔ Forwarding Job)

## Reports and Filters

### List View Filters
- **Pending Conversion**: Shows submitted Job Orders not yet converted
- **By Customer**: Filter by customer name
- **By Date**: Filter by order date
- **By Status**: Draft / Submitted / Converted / Cancelled

### Indicators
- **Gray**: Draft
- **Blue**: Submitted (ready for conversion)
- **Green**: Converted to Forwarding Job
- **Red**: Cancelled

## Benefits

### For Sales Team
- ✓ Clear handover process
- ✓ Know when Operations received the job
- ✓ Track status of accepted quotations
- ✓ Ensure quoted charges match operational charges

### For Operations Team
- ✓ Receive complete job information
- ✓ See exactly what was quoted
- ✓ Document requirements visible early
- ✓ Single click to create Forwarding Job

### For Management
- ✓ Full audit trail
- ✓ Know who handed over what, when
- ✓ Track conversion rates (Quotation → Job Order → Forwarding Job)
- ✓ Identify bottlenecks in handover process

## Troubleshooting

### "Quotation must be in 'Accepted' state"
**Solution**: Ensure the Quotation workflow is in "Accepted" state before creating Job Order.

### "A Job Order already exists for this Quotation"
**Solution**: Check if a Job Order was already created. You can view it from the Quotation form.

### "Cannot cancel Job Order as it has been converted"
**Solution**: This is by design to preserve audit trail. If you need to cancel, first cancel the Forwarding Job, then contact your System Manager.

### Items table is empty
**Solution**: Ensure the Quotation has items. The Job Order automatically fetches items when you select a Quotation Reference.

### Create Forwarding Job button not showing
**Solution**: 
1. Ensure Job Order is submitted (not draft)
2. Check that it hasn't already been converted
3. Verify you have proper permissions

## Installation

The Job Order DocType is automatically installed with FreightMas. To set it up:

1. **Install/Migrate**:
   ```bash
   cd /path/to/frappe-bench
   bench --site your-site migrate
   ```

2. **Import Custom Fields**:
   ```bash
   bench --site your-site import-doc
   ```

3. **Clear Cache**:
   ```bash
   bench --site your-site clear-cache
   ```

4. **Restart**:
   ```bash
   bench restart
   ```

## Future Enhancements

Potential improvements:
- Email notifications on Job Order creation/conversion
- Dashboard showing pending conversions
- Reports on handover timelines
- Integration with other service types (Clearing, Trucking)
- Batch conversion of multiple Job Orders

---

**Created**: January 8, 2026  
**Module**: Forwarding Service  
**Version**: 1.0
