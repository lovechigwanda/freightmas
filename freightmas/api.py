@frappe.whitelist()
def create_journal_entry(trip, charges, debit_accounts):
    charges = json.loads(charges)
    debit_accounts = json.loads(debit_accounts)

    journal_entry = frappe.new_doc("Journal Entry")
    journal_entry.voucher_type = "Journal Entry"
    journal_entry.user_remark = f"Trip: {trip}"
    journal_entry.company = frappe.defaults.get_user_default("Company")
    
    total_amount = 0
    for charge, debit_account in zip(charges, debit_accounts):
        journal_entry.append("accounts", {
            "account": debit_account,
            "debit_in_account_currency": charge.get("amount"),
            "credit_in_account_currency": 0,
            "reference_type": "Trip Other Costs",  # Updated DocType name
            "reference_name": charge.get("name")
        })
        total_amount += charge.get("amount")

    # Credit the Driver Account
    driver_account = frappe.get_value("Trip", trip, "driver_account")
    journal_entry.append("accounts", {
        "account": driver_account,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": total_amount
    })

    journal_entry.insert()
    journal_entry.submit()

    # Update Trip Other Costs as journaled
    for charge in charges:
        frappe.db.set_value("Trip Other Costs", charge.get("name"), "is_journaled", 1)

    return journal_entry.name
