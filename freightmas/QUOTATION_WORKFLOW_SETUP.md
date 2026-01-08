# Quotation Workflow Setup Guide

This guide provides step-by-step instructions for setting up the Quotation Workflow in FreightMas.

## Prerequisites

1. FreightMas app installed
2. User with System Manager role
3. Access to Frappe/ERPNext UI

---

## Part 1: Create Workflow States

Navigate to: **Desk → Workflow → Workflow State → New**

Create the following 8 workflow states **in this exact order**:

### 1. Draft
- **Workflow State Name**: Draft
- **Style**: Default (Gray)
- **Workflow Name**: Quotation Workflow

### 2. Pending Approval
- **Workflow State Name**: Pending Approval
- **Style**: Warning (Orange)
- **Workflow Name**: Quotation Workflow

### 3. Approved
- **Workflow State Name**: Approved
- **Style**: Primary (Blue)
- **Workflow Name**: Quotation Workflow

### 4. Sent to Customer
- **Workflow State Name**: Sent to Customer
- **Style**: Info (Purple)
- **Workflow Name**: Quotation Workflow

### 5. Accepted
- **Workflow State Name**: Accepted
- **Style**: Success (Green)
- **Workflow Name**: Quotation Workflow

### 6. Rejected
- **Workflow State Name**: Rejected
- **Style**: Danger (Red)
- **Workflow Name**: Quotation Workflow

### 7. Expired
- **Workflow State Name**: Expired
- **Style**: Inverse (Dark Gray)
- **Workflow Name**: Quotation Workflow

### 8. Cancelled
- **Workflow State Name**: Cancelled
- **Style**: Danger (Red)
- **Workflow Name**: Quotation Workflow

---

## Part 2: Create Workflow

Navigate to: **Desk → Workflow → Workflow → New**

### Basic Settings
- **Workflow Name**: Quotation Workflow
- **Document Type**: Quotation
- **Workflow State Field**: workflow_state
- **Is Active**: ✓ (Checked)

### States Table

Add all 8 states created above in order:

| State Name       | Doc Status | Allow Edit | Update Field | Update Value |
| ---------------- | ---------- | ---------- | ------------ | ------------ |
| Draft            | 0          | Sales User |              |              |
| Pending Approval | 0          | (None)     |              |              |
| Approved         | 1          | (None)     |              |              |
| Sent to Customer | 1          | (None)     |              |              |
| Accepted         | 1          | (None)     |              |              |
| Rejected         | 1          | (None)     |              |              |
| Expired          | 1          | (None)     |              |              |
| Cancelled        | 2          | (None)     |              |              |

**Important Notes**:
- Only **Draft** state has "Allow Edit" set to Sales User
- **Draft** and **Pending Approval** have Doc Status = 0 (Draft)
- **Approved** through **Expired** have Doc Status = 1 (Submitted)
- **Cancelled** has Doc Status = 2 (Cancelled)

### Transitions Table

Add the following transitions:

| # | State            | Action              | Next State       | Allowed | Condition |
|--:|------------------|---------------------|------------------|---------|-----------|
| 1 | Draft            | Submit for Approval | Pending Approval | Sales User | |
| 2 | Pending Approval | Approve             | Approved         | Sales Manager | |
| 3 | Pending Approval | Reject              | Draft            | Sales Manager | |
| 4 | Approved         | Send to Customer    | Sent to Customer | Sales User | |
| 5 | Approved         | Mark Expired        | Expired          | Sales Manager | |
| 6 | Sent to Customer | Mark Accepted       | Accepted         | Sales Manager | |
| 7 | Sent to Customer | Mark Rejected       | Rejected         | Sales User | |
| 8 | Sent to Customer | Mark Expired        | Expired          | Sales Manager | |
| 9 | Approved         | Cancel              | Cancelled        | Sales Manager | |
| 10| Sent to Customer | Cancel              | Cancelled        | Sales Manager | |
| 11| Accepted         | Cancel              | Cancelled        | Sales Manager | |
| 12| Rejected         | Cancel              | Cancelled        | Sales Manager | |
| 13| Expired          | Cancel              | Cancelled        | Sales Manager | |

**Save the Workflow**

---

## Part 3: Export Fixtures

After creating and testing the workflow, export it to FreightMas app:

```bash
cd /path/to/frappe-bench
bench --site your-site export-fixtures
```

This will update the fixture files in:
- `freightmas/fixtures/workflow.json`
- `freightmas/fixtures/workflow_state.json`
- `freightmas/fixtures/workflow_action_master.json`

---

## Part 4: Verify Automatic Features

The following features are already implemented in code:

### 1. Daily Expiry Check
- **Scheduler**: Runs daily
- **Function**: `freightmas.scheduler.quotation.expire_quotations`
- **Action**: Automatically moves quotations to "Expired" state when valid_till date passes

### 2. Validation
- **Event**: Before Save
- **Function**: `freightmas.freightmas.quotation_workflow.validate_quotation`
- **Rule**: Prevents accepting expired quotations

### 3. Email Notifications
- **Event**: Workflow state change
- **Function**: `freightmas.freightmas.quotation_workflow.on_quotation_workflow_change`
- **Emails Sent**:
  - **Approval Request**: When quotation moves to "Pending Approval" → sent to all Sales Managers
  - **Approval Notification**: When quotation is "Approved" → sent to quotation owner

---

## Part 5: Testing Checklist

Test the following scenarios:

### Basic Flow
- [ ] Create new quotation → starts in "Draft"
- [ ] Submit for Approval → moves to "Pending Approval"
- [ ] Sales Manager receives email notification
- [ ] Approve quotation → moves to "Approved"
- [ ] Quotation owner receives email notification
- [ ] Send to Customer → moves to "Sent to Customer"
- [ ] Mark Accepted → moves to "Accepted"

### Rejection Flow
- [ ] Create and submit quotation
- [ ] Sales Manager rejects → moves back to "Draft"
- [ ] Edit and resubmit

### Expiry (Manual)
- [ ] Approved quotation → Mark Expired → moves to "Expired"
- [ ] Sent to Customer → Mark Expired → moves to "Expired"

### Expiry (Automatic)
- [ ] Create quotation with valid_till = yesterday
- [ ] Approve it (submit)
- [ ] Wait for daily scheduler OR run manually:
  ```bash
  bench --site your-site console
  >>> from freightmas.scheduler.quotation import expire_quotations
  >>> expire_quotations()
  ```
- [ ] Verify quotation moved to "Expired"

### Validation
- [ ] Try to accept a quotation with valid_till in the past
- [ ] Verify error: "Cannot accept an expired quotation"

### Cancellation
- [ ] Approved quotation → Cancel → moves to "Cancelled"
- [ ] Accepted quotation → Cancel → moves to "Cancelled"

### Read-Only Enforcement
- [ ] Approved quotation cannot be edited (docstatus=1)
- [ ] Sent to Customer cannot be edited
- [ ] Accepted cannot be edited

---

## Part 6: Common Issues & Solutions

### Issue: Workflow not appearing on Quotation form
**Solution**: Clear cache
```bash
bench --site your-site clear-cache
```

### Issue: Email notifications not sending
**Solution**: Check email queue
```bash
bench --site your-site console
>>> frappe.db.sql("SELECT * FROM `tabEmail Queue` ORDER BY creation DESC LIMIT 10", as_dict=1)
```

### Issue: Scheduler not running
**Solution**: Verify scheduler is enabled
```bash
bench --site your-site enable-scheduler
bench doctor
```

### Issue: States not showing colors
**Solution**: Verify "Style" is set for each Workflow State

---

## Part 7: Deployment to Other Sites

Once fixtures are exported:

1. **Commit changes to git**:
   ```bash
   cd apps/freightmas
   git add .
   git commit -m "Add Quotation Workflow"
   git push
   ```

2. **On new site**:
   ```bash
   cd /path/to/frappe-bench
   bench --site new-site migrate
   bench --site new-site clear-cache
   ```

The workflow will be automatically installed from fixtures!

---

## Part 8: Customization

To modify the workflow later:

1. Make changes via UI (Workflow form)
2. Export fixtures again: `bench --site your-site export-fixtures`
3. Commit to git
4. Migrate other sites

---

## Support

For issues or questions:
- Check Frappe/ERPNext documentation on Workflows
- Review error logs: `bench --site your-site logs`
- Contact: info@zvomaita.co.zw

---

**END OF SETUP GUIDE**
