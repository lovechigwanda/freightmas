# FreightMas Installation Verification Guide

Use this guide to verify that FreightMas has been successfully cloned and installed in your environment.

## ✅ Pre-Installation Checklist

Before installing FreightMas, verify:

- [ ] Python 3.10 or higher installed: `python3 --version`
- [ ] Node.js 18 or higher installed: `node --version`
- [ ] MariaDB installed and running: `sudo systemctl status mariadb`
- [ ] Redis installed and running: `sudo systemctl status redis`
- [ ] Frappe bench initialized: `bench --version`
- [ ] Site created: `ls ~/frappe-bench/sites/`
- [ ] ERPNext installed: `bench --site [site] list-apps | grep erpnext`

## ✅ Installation Verification

### Step 1: Verify App Files Exist

```bash
cd ~/frappe-bench/apps
ls -la freightmas
```

**Expected**: Directory should exist with these key folders:
- `freightmas/` (main app directory)
- `clearing_service/`
- `trucking_service/`
- `forwarding_service/`
- `road_freight_service/`
- `warehouse_service/`

**Status**: [ ] PASS / [ ] FAIL

---

### Step 2: Verify App is Installed on Site

```bash
bench --site [your-site] list-apps
```

**Expected Output** (should include):
```
frappe
erpnext
freightmas
```

**Status**: [ ] PASS / [ ] FAIL

---

### Step 3: Verify Database Tables Created

```bash
bench --site [your-site] console
```

Then in the console:
```python
import frappe
frappe.get_all('DocType', filters={'module': 'Port Clearing Service'}, fields=['name'])
```

**Expected**: Should return a list of doctypes like:
- ClearingJob
- ClearingCharges
- ClearingChargesTemplate
- etc.

**Status**: [ ] PASS / [ ] FAIL

Exit console: `exit()`

---

### Step 4: Verify Workspaces are Available

```bash
bench --site [your-site] console
```

Then:
```python
import frappe
workspaces = frappe.get_all('Workspace', filters={'app': 'freightmas'}, fields=['name'])
print([w.name for w in workspaces])
```

**Expected Workspaces**:
- Port Clearing Service
- Trucking Service
- Forwarding Service
- Road Freight Service

**Status**: [ ] PASS / [ ] FAIL

Exit console: `exit()`

---

### Step 5: Verify Static Assets Built

```bash
ls -la ~/frappe-bench/sites/assets/freightmas/
```

**Expected**: Should see built JavaScript and CSS files

**Status**: [ ] PASS / [ ] FAIL

---

### Step 6: Verify Fixtures Imported

```bash
bench --site [your-site] console
```

Then:
```python
import frappe
# Check if custom fields exist
custom_fields = frappe.get_all('Custom Field', filters={'module': 'FreightMas'})
print(f"Custom Fields: {len(custom_fields)}")
```

**Expected**: Should show multiple custom fields (>0)

**Status**: [ ] PASS / [ ] FAIL

Exit console: `exit()`

---

### Step 7: Test Web Access

1. Start bench (if not already running):
   ```bash
   bench start
   ```

2. Open browser: `http://[your-site]:8000`

3. Login with Administrator credentials

**Expected**: Should reach login page and successfully login

**Status**: [ ] PASS / [ ] FAIL

---

### Step 8: Verify Module Access

In the web interface:

1. Click on the search bar (or press Ctrl+K / Cmd+K)
2. Type: "Port Clearing Service"
3. Click on the workspace

**Expected**: Should open FreightMas Port Clearing Service workspace

**Status**: [ ] PASS / [ ] FAIL

---

### Step 9: Test DocType Creation

1. Navigate to Port Clearing Service workspace
2. Click "New Clearing Job" (or similar)
3. Try to open the form

**Expected**: Form should open without errors

**Status**: [ ] PASS / [ ] FAIL

---

### Step 10: Verify No Console Errors

1. Open Browser Developer Tools (F12)
2. Navigate to Console tab
3. Navigate through FreightMas modules

**Expected**: No red errors in console (warnings are okay)

**Status**: [ ] PASS / [ ] FAIL

---

## 🧪 Functional Tests

### Test 1: API Endpoint Access

```bash
bench --site [your-site] console
```

Then:
```python
import frappe
frappe.local.request = None
# Test if FreightMas API methods are accessible
from freightmas import api
print("API module loaded successfully")
```

**Status**: [ ] PASS / [ ] FAIL

---

### Test 2: Create Sample Document

Try creating a sample document through the UI:

1. Go to a FreightMas module
2. Create a new document
3. Fill required fields
4. Save

**Expected**: Document saves successfully

**Status**: [ ] PASS / [ ] FAIL

---

### Test 3: Run a Report

1. Navigate to any FreightMas report
2. Set filters
3. Click "Refresh"

**Expected**: Report loads with data or "No data" message

**Status**: [ ] PASS / [ ] FAIL

---

## 🔍 Diagnostic Commands

If any checks fail, run these diagnostic commands:

### Check Frappe Version
```bash
bench version
```

### Check Site Database Connection
```bash
bench --site [your-site] mariadb
```
Then: `SHOW TABLES LIKE '%Clearing%';`
Exit: `exit`

### Check for Migration Errors
```bash
bench --site [your-site] migrate
```

### Rebuild Assets
```bash
bench build --app freightmas
```

### Check Logs
```bash
# View bench logs
tail -f ~/frappe-bench/logs/bench-start.log

# View site error log
bench --site [your-site] logs
```

### Clear All Caches
```bash
bench --site [your-site] clear-cache
bench --site [your-site] clear-website-cache
```

---

## 📋 Complete Verification Summary

### Quick Checklist

Installation Verification:
- [ ] App files exist in apps/freightmas
- [ ] App listed in `bench list-apps`
- [ ] Database tables created
- [ ] Workspaces available
- [ ] Static assets built
- [ ] Fixtures imported
- [ ] Web access works
- [ ] Modules accessible
- [ ] DocTypes work
- [ ] No console errors

Functional Tests:
- [ ] API accessible
- [ ] Can create documents
- [ ] Reports work

---

## 🎯 Success Criteria

**Installation is successful if:**

✅ All 10 verification steps PASS  
✅ All 3 functional tests PASS  
✅ No critical errors in logs  
✅ All workspaces accessible  

---

## 🚨 Common Issues and Solutions

### Issue: FreightMas not in `list-apps`

**Solution:**
```bash
bench --site [your-site] install-app freightmas
```

---

### Issue: Workspaces not showing

**Solution:**
```bash
bench --site [your-site] migrate
bench --site [your-site] clear-cache
bench restart
```

---

### Issue: Console errors on page load

**Solution:**
```bash
bench build --app freightmas
bench restart
```

---

### Issue: Database tables missing

**Solution:**
```bash
bench --site [your-site] migrate --skip-search-index
```

---

### Issue: "Module not found" errors

**Solution:**
```bash
cd ~/frappe-bench/apps/freightmas
pip install -e .
cd ~/frappe-bench
bench restart
```

---

## 📊 Verification Report Template

Copy and fill this out to document your installation:

```
FreightMas Installation Verification Report
==========================================

Date: _______________
Site Name: _______________
Bench Path: _______________
FreightMas Version: _______________

Pre-Installation Checklist:
[ ] Python version: _______________
[ ] Node version: _______________
[ ] MariaDB status: _______________
[ ] Redis status: _______________
[ ] Bench version: _______________

Installation Verification:
[ ] Step 1: App Files
[ ] Step 2: App Installed
[ ] Step 3: Database Tables
[ ] Step 4: Workspaces
[ ] Step 5: Static Assets
[ ] Step 6: Fixtures
[ ] Step 7: Web Access
[ ] Step 8: Module Access
[ ] Step 9: DocType Creation
[ ] Step 10: Console Check

Functional Tests:
[ ] Test 1: API Access
[ ] Test 2: Sample Document
[ ] Test 3: Reports

Overall Result: [ ] SUCCESS / [ ] FAILED

Notes:
_________________________________
_________________________________
_________________________________

Verified by: _______________
```

---

## 🆘 Need Help?

If your installation fails verification:

1. **Check Logs**: Look for specific error messages
2. **Review Documentation**: CLONING_GUIDE.md has troubleshooting
3. **Search Issues**: Check GitHub issues for similar problems
4. **Ask for Help**: Create a new issue with your verification report

---

## ✨ Post-Verification Steps

Once verified successfully:

1. **Set up basic data**:
   - Create test customers
   - Create test suppliers
   - Set up service items

2. **Explore features**:
   - Navigate through each service module
   - Review available reports
   - Check print formats

3. **Read documentation**:
   - Service-specific guides
   - User manuals in module folders
   - API documentation

4. **Start using FreightMas**! 🚚📦

---

**Happy FreightMas-ing!**

Last Updated: January 2026

