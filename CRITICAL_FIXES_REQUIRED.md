# REVENUE RECOGNITION SYSTEM - CRITICAL FIXES REQUIRED

## Priority P0 - MUST FIX BEFORE PRODUCTION

---

## FIX #1: RACE CONDITION in Late Invoice Total Updates

### Location
File: `freightmas/utils/revenue_recognition.py`
Lines: 1025-1035 (Sales) and similar for Purchase Invoices

### Current Code (UNSAFE)
```python
def handle_late_invoice_submission(invoice_doc, job_doctype, job_link_field, service_type):
    # ... earlier code ...
    
    # UNSAFE: Race condition
    current_total = flt(frappe.db.get_value(job_doctype, job_reference, "total_recognised_revenue"))
    frappe.db.set_value(job_doctype, job_reference,
        "total_recognised_revenue", current_total + amount,
        update_modified=False)  # ← PROBLEM: Not atomic
```

### Problem Scenario
```
Timeline:
T0: Invoice A handler reads total = 0, calculates 0 + 100 = 100
T1: Invoice B handler reads total = 0, calculates 0 + 200 = 200
T2: Invoice A writes total = 100 ✓
T3: Invoice B writes total = 200 ✗ (SHOULD BE 300, LOST £100)

Result: Revenue understated by £100
```

### Fixed Code (ATOMIC)
```python
def handle_late_invoice_submission(invoice_doc, job_doctype, job_link_field, service_type):
    # ... earlier code ...
    
    # FIXED: Atomic database update
    frappe.db.sql("""
        UPDATE `tab{job_doctype}`
        SET total_recognised_revenue = total_recognised_revenue + %s,
            modified = %s
        WHERE name = %s
    """.format(job_doctype=job_doctype), (amount, frappe.utils.now(), job_reference))
    
    # Similarly for cost:
    frappe.db.sql("""
        UPDATE `tab{job_doctype}`
        SET total_recognised_cost = total_recognised_cost + %s,
            modified = %s
        WHERE name = %s
    """.format(job_doctype=job_doctype), (amount, frappe.utils.now(), job_reference))
```

### Test Case to Verify Fix
```python
def test_concurrent_late_invoices():
    """Verify race condition is fixed"""
    import threading
    
    job = create_test_job()
    job.on_submit()
    
    # Create 10 invoices submitted concurrently
    invoices = [create_and_submit_late_invoice(job) for _ in range(10)]
    
    total_amounts = [100, 200, 150, 300, 50, 100, 75, 125, 200, 175]
    expected_total = sum(total_amounts)
    
    threads = []
    for inv, amount in zip(invoices, total_amounts):
        t = threading.Thread(target=handle_late_invoice_submission, 
                            args=(inv, job.doctype, "job_reference", "clearing"))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    job.reload()
    assert job.total_recognised_revenue == expected_total, \
        f"Expected {expected_total}, got {job.total_recognised_revenue}"
```

---

## FIX #2: MISSING ROLLBACK on Journal Entry Submission Failure

### Location
File: `freightmas/utils/revenue_recognition.py`
Lines: 486-500 (Revenue) and 550-565 (Cost)

### Current Code (UNSAFE)
```python
def create_recognition_journal_entry(job_doc, invoices, recognition_date, service_type):
    # ... build journal entry ...
    
    je = frappe.get_doc({...})
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()  # ← IF THIS FAILS, job_doc is already marked recognized
    
    frappe.msgprint(...)
    return je.name, total_recognized
    # No exception handling - any error here leaves dangling state
```

### Problem Scenario
```
Scenario: Account Disabled After Invoice Created
1. Invoice created with "Forwarding Revenue" account enabled ✓
2. Admin disables "Forwarding Revenue" account
3. Job submitted (on_submit triggered)
4. JE created successfully (inserted)
5. JE.submit() fails: Account disabled validation error
6. Exception thrown, on_submit handler aborts
7. BUT: Job document already has revenue_recognised = 1 in database ✗

Result: 
- Job appears recognized (flag = 1)
- But JE doesn't exist (no accounting posted)
- GL is unbalanced, financial statements wrong
```

### Fixed Code (WITH ROLLBACK)
```python
def create_recognition_journal_entry(job_doc, invoices, recognition_date, service_type):
    """
    Create a Journal Entry to recognize revenue for completed job.
    
    Returns:
        tuple: (je_name, total_recognized), or (None, 0) if creation fails
               NOTE: Does NOT modify job_doc on failure (caller must handle)
    """
    if not invoices:
        frappe.throw(_("No invoices found for revenue recognition"))

    wip_revenue_account = get_wip_revenue_account()
    
    # ... build accounts list ...
    
    if not accounts:
        return None, 0

    # Create Journal Entry
    try:
        je = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": recognition_date,
            "company": job_doc.company,
            "user_remark": _("Revenue Recognition for {0} {1}").format(
                job_doc.doctype, job_doc.name
            ),
            "accounts": accounts,
        })
        
        je.flags.ignore_permissions = True
        je.insert()
        je.submit()
        
        frappe.msgprint(
            _("Revenue Recognition Journal Entry {0} created for {1}").format(
                get_link_to_form("Journal Entry", je.name),
                frappe.format_value(total_recognized, {"fieldtype": "Currency"})
            ),
            alert=True
        )
        
        return je.name, total_recognized
        
    except Exception as e:
        # Log error and re-throw - do NOT update job_doc
        error_msg = str(e)
        frappe.log_error(
            f"Revenue Recognition JE submission failed: {error_msg}\n"
            f"Job: {job_doc.doctype} {job_doc.name}\n"
            f"Total to recognize: {total_recognized}\n"
            f"Please fix the issue and re-submit the job.",
            "Revenue Recognition Failure"
        )
        
        # Re-throw with user-friendly message
        frappe.throw(
            _("Failed to create Revenue Recognition Journal Entry: {0}\n\n"
              "Please ensure:\n"
              "1. All revenue accounts are configured and enabled\n"
              "2. The GL period is open\n"
              "3. The accounting date is not in the past\n\n"
              "Job submission ABORTED. Fix the issue and try again.").format(error_msg)
        )


def recognize_revenue_for_job(job_doc, service_type):
    """
    Main function to recognize revenue when a job is submitted.
    
    Args:
        job_doc: The job document being submitted
        service_type: One of 'forwarding', 'trucking', 'clearing', 'road_freight'
    
    Raises:
        frappe.ValidationError if recognition fails
    """
    if not is_revenue_recognition_enabled():
        return
    
    if job_doc.revenue_recognised:
        frappe.throw(
            _("Revenue has already been recognised for this job. "
              "Journal Entry: {0}").format(job_doc.revenue_recognition_journal_entry)
        )
    
    if not job_doc.revenue_recognised_on:
        frappe.throw(
            _("Please set the Revenue Recognition Date before submitting the job")
        )
    
    # Get all submitted sales invoices linked to this job
    invoices = get_linked_sales_invoices(job_doc.doctype, job_doc.name)
    invoices = [inv for inv in invoices if flt(inv.grand_total) > 0]

    if not invoices:
        frappe.msgprint(
            _("No Sales Invoices with non-zero amounts linked to this job for revenue recognition."),
            alert=True
        )
        job_doc.revenue_recognised = 1
        job_doc.total_recognised_revenue = 0
        return
    
    # Validate RR date is not before earliest invoice date
    from frappe.utils import getdate
    rr_date = getdate(job_doc.revenue_recognised_on)
    earliest_invoice_date = min(getdate(inv.posting_date) for inv in invoices)
    
    if rr_date < earliest_invoice_date:
        frappe.throw(
            _("Revenue Recognition Date ({0}) cannot be earlier than the earliest "
              "invoice date ({1}). The WIP Revenue account would not have a "
              "balance to recognize from.").format(
                frappe.format_value(rr_date, {"fieldtype": "Date"}),
                frappe.format_value(earliest_invoice_date, {"fieldtype": "Date"})
            )
        )
    
    # Create recognition Journal Entry
    # NOTE: create_recognition_journal_entry will throw if it fails
    # This prevents on_submit from completing if recognition fails
    je_name, total_recognized = create_recognition_journal_entry(
        job_doc,
        invoices,
        job_doc.revenue_recognised_on,
        service_type
    )

    if not je_name:
        # Nothing parked in WIP (e.g. pass-through-only invoices) — never block closure
        frappe.msgprint(
            _("Linked Sales Invoices have no WIP Revenue balance to recognize."),
            alert=True
        )
        job_doc.revenue_recognised = 1
        job_doc.total_recognised_revenue = 0
        return

    # ONLY update job if JE creation succeeded
    job_doc.revenue_recognised = 1
    job_doc.revenue_recognition_journal_entry = je_name
    job_doc.total_recognised_revenue = total_recognized
```

### Test Case to Verify Fix
```python
def test_je_submission_failure_doesnt_mark_recognized():
    """Verify that job is NOT marked recognized if JE submission fails"""
    
    job = create_test_job()
    invoice = create_and_submit_test_invoice(job)
    
    # Disable the revenue account
    frappe.db.set_value("Account", "Forwarding Revenue", "disabled", 1)
    
    try:
        job.on_submit()
        assert False, "Should have thrown error"
    except frappe.ValidationError:
        pass  # Expected
    finally:
        # Re-enable account
        frappe.db.set_value("Account", "Forwarding Revenue", "disabled", 0)
    
    job.reload()
    # KEY ASSERTION: revenue_recognised should still be 0
    assert job.revenue_recognised == 0, \
        "Job should NOT be marked recognized if JE submission fails"
    assert not job.revenue_recognition_journal_entry, \
        "Job should have no JE reference"
```

---

## FIX #3: VALIDATE WIP Account Type at Configuration Time

### Location
File: `freightmas/utils/revenue_recognition.py`
New validation needed in `get_recognition_settings()`

### Current Code (NO VALIDATION)
```python
def get_recognition_settings():
    """Fetch revenue/cost recognition settings from FreightMas Settings."""
    settings = frappe.get_single("FreightMas Settings")
    return {
        "enabled": settings.enable_revenue_recognition,
        "wip_revenue_account": settings.wip_revenue_account,  # ← NO TYPE CHECK
        "wip_cost_account": settings.wip_cost_account,        # ← NO TYPE CHECK
        ...
    }
```

### Problem Scenario
```
Misconfiguration Example:
Admin sets: WIP Revenue Account = "Forwarding Revenue" (INCOME account, not LIABILITY)

Wrong Accounting:
Invoice: Dr A/R, Cr Forwarding Revenue (skips WIP entirely!) ✗
Job:     Dr WIP, Cr Forwarding Revenue (creates duplicate entry) ✗

Result: Revenue appears TWICE
Journal Entry totals: £2,000
Actual revenue: £1,000
Overstatement: 100%
```

### Fixed Code (WITH VALIDATION)
```python
def validate_wip_account_type(account_name, expected_type):
    """
    Validate that an account exists and has the expected type.
    
    Args:
        account_name: Account name to validate
        expected_type: Expected account_type (e.g., 'Liability', 'Asset')
    
    Returns:
        str: account_name if valid
        
    Raises:
        frappe.ValidationError: If account is invalid
    """
    if not account_name:
        return None
    
    acc = frappe.db.get_value(
        "Account",
        account_name,
        ["account_type", "disabled", "is_group", "company"],
        as_dict=True
    )
    
    if not acc:
        frappe.throw(
            _("Account {0} does not exist").format(account_name)
        )
    
    if acc.is_group:
        frappe.throw(
            _("Account {0} is a group account, not a ledger").format(account_name)
        )
    
    if acc.disabled:
        frappe.throw(
            _("Account {0} is disabled").format(account_name)
        )
    
    if acc.account_type != expected_type:
        frappe.throw(
            _("WIP Account {0} must be {1}, but is {2}").format(
                account_name, expected_type, acc.account_type
            )
        )
    
    return account_name


def get_recognition_settings():
    """
    Fetch and validate revenue/cost recognition settings from FreightMas Settings.
    
    Returns:
        dict: Settings including enable flag, validated accounts
        
    Raises:
        frappe.ValidationError: If any account is misconfigured
    """
    settings = frappe.get_single("FreightMas Settings")
    
    if not settings.enable_revenue_recognition:
        return {"enabled": False}
    
    # Validate WIP accounts (must be LIABILITY)
    wip_revenue = validate_wip_account_type(
        settings.wip_revenue_account,
        "Liability"
    )
    wip_cost = validate_wip_account_type(
        settings.wip_cost_account,
        "Asset"
    )
    
    # Build service accounts and validate (must be INCOME/EXPENSE)
    service_accounts = {}
    for service_type in ["forwarding", "clearing", "border_clearing", "trucking", "road_freight"]:
        revenue_key = f"{service_type}_revenue_account"
        cost_key = f"{service_type}_cost_account"
        
        revenue_acct = getattr(settings, revenue_key, None)
        if revenue_acct:
            validate_wip_account_type(revenue_acct, "Income")
            service_accounts[revenue_key] = revenue_acct
        
        cost_acct = getattr(settings, cost_key, None)
        if cost_acct:
            validate_wip_account_type(cost_acct, "Expense")
            service_accounts[cost_key] = cost_acct
    
    return {
        "enabled": True,
        "wip_revenue_account": wip_revenue,
        "wip_cost_account": wip_cost,
        "pass_through_account": settings.duty_pass_through_account,
        **service_accounts
    }


def get_service_revenue_account(service_type):
    """Get the revenue account for a specific service type."""
    settings = get_recognition_settings()  # Now validates accounts
    account_key = f"{service_type}_revenue_account"
    account = settings.get(account_key)
    if not account:
        frappe.throw(
            _("{0} Revenue Account not configured in FreightMas Settings").format(
                service_type.replace("_", " ").title()
            )
        )
    return account
```

### Where to Add the Validation
Add to `FreightMas Settings` doctype (doctype validation):
```python
# In freightmas/freightmas/doctype/freightmas_settings/freightmas_settings.py

def validate(self):
    """Validate settings when saved"""
    if self.enable_revenue_recognition:
        # Trigger account validation
        from freightmas.utils.revenue_recognition import get_recognition_settings
        try:
            get_recognition_settings()
        except frappe.ValidationError as e:
            # Re-raise with context
            frappe.throw(
                _("Revenue Recognition Settings are invalid:\n{0}").format(str(e))
            )
```

---

## FIX #4: CURRENCY CONVERSION TIMING

### Location
File: `freightmas/clearing_service/doctype/clearing_job/clearing_job.py`
Lines: 94-105

### Current Code (UNSAFE)
```python
def set_base_currency(self):
    """Ensure base_currency and conversion_rate are set."""
    if not getattr(self, "base_currency", None) and getattr(self, "company", None):
        self.base_currency = frappe.db.get_value("Company", self.company, "default_currency")

    if not getattr(self, "conversion_rate", None):
        try:
            from erpnext.setup.utils import get_exchange_rate
            if self.currency and self.base_currency and self.currency != self.base_currency:
                # PROBLEM: Gets TODAY's rate, not invoice's rate
                self.conversion_rate = flt(get_exchange_rate(self.currency, self.base_currency)) or 1.0
            else:
                self.conversion_rate = 1.0
        except Exception:
            self.conversion_rate = 1.0
```

### Problem Scenario
```
Timeline:
2024-01-01: Invoice created in USD, rate = 0.85 GBP/USD
           WIP Revenue entry: USD 1000 @ 0.85 = GBP 850
           Item.base_net_amount = 850

2024-01-31: Job submitted, rate = 0.80 GBP/USD (changed!)
           Revenue recognition tries to reverse GBP 850
           But uses new rate 0.80 to post to final account
           Calculation: 1000 * 0.80 = 800 (different!)
           
GL Entry: Dr WIP 850, Cr Revenue 800
Result: GL UNBALANCED by 50 ✗
```

### Key Insight
- Invoice items have `base_net_amount` (already converted at invoice time)
- Job doesn't need to recalculate currency conversion
- Just use item.base_net_amount directly

### Fixed Code
```python
def set_base_currency(self):
    """Set base_currency from Company - DO NOT recalculate conversion_rate"""
    if not getattr(self, "base_currency", None) and getattr(self, "company", None):
        self.base_currency = frappe.db.get_value("Company", self.company, "default_currency")
    
    # FIXED: Remove conversion_rate calculation from here
    # All invoice amounts are already in base currency (base_net_amount)
    # Conversion happened at invoice creation time, not job submission
    # Using different rate here would break GL reconciliation


# In revenue_recognition.py, build_recognition_lines():
def build_recognition_lines(invoice, job_doc, wip_account, snapshot_field,
                            invoice_account_field, get_fallback_account, remark_builder, side):
    """
    Build per-charge recognition JE lines for one invoice.
    
    KEY: Always use invoice.items[].base_net_amount
    This is already in company's base currency (converted at invoice time)
    """
    company = job_doc.company
    item_side = "credit_in_account_currency" if side == "revenue" else "debit_in_account_currency"
    wip_side = "debit_in_account_currency" if side == "revenue" else "credit_in_account_currency"

    lines = []
    included_total = 0

    for item in invoice.items:
        if item.get(invoice_account_field) != wip_account:
            continue
        
        # FIXED: Use base_net_amount (already converted)
        # DO NOT use item.net_amount (would recalculate with different rate)
        amount = flt(item.base_net_amount)
        if amount <= 0:
            continue
        
        target = item.get(snapshot_field)
        if not is_usable_account(target, company):
            target = get_fallback_account()

        remark = remark_builder(item.item_name or item.item_code)
        lines.append({
            "account": wip_account,
            wip_side: amount,
            "cost_center": item.cost_center,
            "user_remark": remark,
        })
        lines.append({
            "account": target,
            item_side: amount,
            "cost_center": item.cost_center,
            "user_remark": remark,
        })
        included_total = flt(included_total + amount, 2)

    if included_total <= 0:
        return [], 0

    return lines, included_total
```

### Test Case
```python
def test_multi_currency_revenue_recognition():
    """Verify GL balances with multi-currency invoices"""
    
    company = create_test_company(currency="GBP")
    
    # Create job
    job = create_test_job(company=company)
    
    # Create invoice in USD on 2024-01-01 (rate 0.85)
    invoice = create_test_invoice(
        company=company,
        currency="USD",
        job=job,
        posting_date="2024-01-01",
        amount=1000,  # USD
        # Item base_net_amount should be 850 (1000 * 0.85)
    )
    
    # Get the actual base_net_amount
    invoice.reload()
    expected_base_amount = invoice.items[0].base_net_amount
    
    # Submit job on 2024-01-31 (rate now 0.80, but should be ignored)
    job.submission_date = "2024-01-31"
    job.on_submit()
    
    # Verify GL entries
    revenue_je = frappe.get_doc("Journal Entry", job.revenue_recognition_journal_entry)
    
    wip_lines = [acc for acc in revenue_je.accounts if acc.account == "WIP Revenue"]
    revenue_lines = [acc for acc in revenue_je.accounts if acc.account == "Forwarding Revenue"]
    
    # Both should be equal to base_net_amount
    assert wip_lines[0].debit_in_account_currency == expected_base_amount
    assert revenue_lines[0].credit_in_account_currency == expected_base_amount
    
    # GL should be balanced
    total_debit = sum(flt(acc.debit_in_account_currency) for acc in revenue_je.accounts)
    total_credit = sum(flt(acc.credit_in_account_currency) for acc in revenue_je.accounts)
    assert total_debit == total_credit, \
        f"GL unbalanced: debit {total_debit} != credit {total_credit}"
```

---

## FIX #5: DATABASE-LEVEL CONCURRENCY PROTECTION for Late Invoices

### Location
File: `freightmas/utils/revenue_recognition.py`
Lines: 967-1037

### Current Code (VULNERABLE TO DUPLICATE)
```python
def handle_late_invoice_submission(invoice_doc, job_doctype, job_link_field, service_type):
    # ...
    # Guard: do not double-recognise if this invoice already has a recognition JE
    if frappe.db.get_value("Sales Invoice", invoice_doc.name, "recognition_journal_entry"):
        return  # ← Race condition: two threads check simultaneously, both see NULL
```

### Problem Scenario
```
Concurrent Timeline:
T0: Thread A checks SI "recognition_journal_entry" = NULL ✓
T0: Thread B checks SI "recognition_journal_entry" = NULL ✓
T1: Thread A creates JE-001 ✓
T2: Thread B creates JE-002 ✓
T3: Thread A saves "SI.recognition_journal_entry = JE-001" ✓
T4: Thread B saves "SI.recognition_journal_entry = JE-002" ✗ (overwrites!)

Result: 
- Two JEs created (JE-001 and JE-002)
- SI only references JE-002 (JE-001 is orphaned)
- Job total_recognised_revenue incremented twice
- Revenue OVERSTATED by duplicate amount
```

### Fixed Code (Database Lock + Constraint)
```python
def handle_late_invoice_submission(invoice_doc, job_doctype, job_link_field, service_type):
    """
    Handle submission of an invoice after the linked job is already recognized.
    Creates an immediate recognition JE for this invoice.
    
    Uses database lock to prevent race conditions with concurrent submissions.
    """
    if not is_revenue_recognition_enabled():
        return

    job_reference = getattr(invoice_doc, job_link_field, None)
    if not job_reference:
        return

    # FIXED: Use database-level lock to prevent concurrent processing
    try:
        # Lock the invoice row for update until transaction commits
        frappe.db.sql("""
            SELECT * FROM `tabSales Invoice` 
            WHERE name = %s
            FOR UPDATE
        """, invoice_doc.name)
    except Exception as e:
        frappe.log_error(f"Failed to acquire lock on {invoice_doc.name}: {e}",
                        "Revenue Recognition")
        frappe.throw(_("Failed to acquire lock for invoice processing. Please retry."))

    # Now check - even if we waited for lock, still verify
    recognition_je = frappe.db.get_value(
        "Sales Invoice", 
        invoice_doc.name,
        "recognition_journal_entry"
    )
    if recognition_je:
        frappe.msgprint(
            _("Invoice {0} already has recognition JE: {1}").format(
                invoice_doc.name, recognition_je
            ),
            alert=True
        )
        return

    job_doc = frappe.get_doc(job_doctype, job_reference)

    # Check if job already has revenue recognized
    if not job_doc.revenue_recognised or not job_doc.revenue_recognised_on:
        return

    # Check if invoice has zero amount - skip recognition
    invoice_amount = flt(invoice_doc.grand_total)
    if invoice_amount <= 0:
        frappe.msgprint(
            _("Sales Invoice {0} has zero amount. Skipping revenue recognition.").format(
                invoice_doc.name
            ),
            alert=True
        )
        return

    # Create immediate recognition for this invoice
    je_name, amount = create_single_invoice_recognition_je(
        job_doc,
        invoice_doc,
        nowdate(),
        service_type
    )

    if not je_name:
        frappe.msgprint(
            _("Sales Invoice {0} has no WIP Revenue balance. Skipping revenue recognition.").format(
                invoice_doc.name
            ),
            alert=True
        )
        return

    # FIXED: Atomic update with lock held
    frappe.db.sql("""
        UPDATE `tabSales Invoice`
        SET recognition_journal_entry = %s,
            modified = %s
        WHERE name = %s
    """, (je_name, frappe.utils.now(), invoice_doc.name))
    
    # Also atomically increment job total
    frappe.db.sql("""
        UPDATE `tab{0}`
        SET total_recognised_revenue = total_recognised_revenue + %s,
            modified = %s
        WHERE name = %s
    """.format(job_doctype), (amount, frappe.utils.now(), job_reference))

    frappe.msgprint(
        _("Late invoice revenue recognized immediately. Journal Entry: {0}").format(
            get_link_to_form("Journal Entry", je_name)
        ),
        alert=True
    )
```

### Database Schema Changes (in migration)
```python
# Add unique constraint to prevent double-recognition even at database level
def execute():
    """Add unique index to prevent duplicate late-invoice recognition"""
    
    # For Sales Invoice
    try:
        frappe.db.sql("""
            ALTER TABLE `tabSales Invoice`
            ADD UNIQUE KEY unique_recognition_je 
            (recognition_journal_entry)
            WHERE recognition_journal_entry IS NOT NULL
        """)
    except Exception as e:
        if "Duplicate key" not in str(e):
            raise
    
    # For Purchase Invoice  
    try:
        frappe.db.sql("""
            ALTER TABLE `tabPurchase Invoice`
            ADD UNIQUE KEY unique_recognition_je 
            (recognition_journal_entry)
            WHERE recognition_journal_entry IS NOT NULL
        """)
    except Exception as e:
        if "Duplicate key" not in str(e):
            raise
```

### Test Case
```python
def test_late_invoice_concurrency():
    """Verify that concurrent late invoice submissions don't create duplicates"""
    
    import threading
    import time
    
    job = create_test_job()
    job.on_submit()
    job.reload()
    
    # Create invoice but don't submit yet
    invoice = create_test_invoice(job=job, submit=False)
    
    # Function to submit invoice with delay
    def submit_invoice():
        time.sleep(0.1)  # Ensure concurrent submission
        invoice.submit()
    
    # Try to submit from multiple threads simultaneously
    threads = []
    for _ in range(5):
        t = threading.Thread(target=submit_invoice)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Verify only ONE JE was created
    invoice.reload()
    je_name = invoice.recognition_journal_entry
    
    # Verify job total is correct (not doubled/tripled)
    job.reload()
    expected_total = invoice.total
    assert job.total_recognised_revenue == expected_total, \
        f"Expected {expected_total}, got {job.total_recognised_revenue}"
    
    # Verify JE exists and is unique
    assert je_name, "JE should be created"
    
    # Query to find all JEs for this invoice (should be only 1)
    all_jes_for_invoice = frappe.db.get_all(
        "Journal Entry Account",
        filters={"user_remark": ("like", f"%{invoice.name}%")},
        fields=["parent"],
        distinct=True
    )
    
    assert len(all_jes_for_invoice) == 1, \
        f"Expected 1 JE, found {len(all_jes_for_invoice)}: {all_jes_for_invoice}"
```

---

## Summary of Fixes

| Fix | Severity | Effort | Time | Risk Level |
|-----|----------|--------|------|-----------|
| #1 Race Condition | CRITICAL | Medium | 45 min | HIGH |
| #2 Rollback Missing | CRITICAL | Medium | 60 min | HIGH |
| #3 WIP Type Validation | CRITICAL | Medium | 90 min | HIGH |
| #4 Currency Timing | CRITICAL | Low | 60 min | HIGH |
| #5 Late Invoice Concurrency | CRITICAL | High | 120 min | HIGH |

**Total Estimated Effort: 8.25 hours**

---

**Next Steps:**
1. Create feature branch: `git checkout -b fix/revenue-recognition-critical-issues`
2. Implement fixes in priority order (1-5)
3. Add test cases for each fix
4. Code review with team
5. Deploy to staging for full integration testing
6. Verify with accounting team
7. Deploy to production with monitoring

