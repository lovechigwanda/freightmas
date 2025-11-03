# FreightMas AI Coding Instructions

## Application Overview
FreightMas is a comprehensive Frappe application for freight and logistics management, built on ERPNext. It manages four core service domains: **Port Clearing**, **Trucking**, **Forwarding**, and **Road Freight** services. Each service operates as a semi-autonomous module with dedicated doctypes, reports, and workflows.

## Architecture Patterns

### Service Module Structure
Each service follows a consistent structure:
```
{service}_service/
├── doctype/           # Core business objects
├── report/            # Service-specific reports  
├── workspace/         # Service workspace UI
├── number_card/       # Dashboard metrics
└── print_format/      # Document templates
```

### Core Business Objects
- **Job Documents**: `ClearingJob`, `Trip`, `ForwardingJob`, `RoadFreightJob` - Central business transactions
- **Charges**: Revenue/cost line items with customer/supplier mapping (`clearing_charges`, `trip_revenue_charges`, `trip_cost_charges`)
- **Templates**: Standardized charge sets (`ClearingChargesTemplate`)
- **Master Data**: Routes, trucks, shipping lines, container types

### Invoice Generation Pattern
All services use a consistent invoice creation pattern:
1. **Selection-based invoicing** - Users select charges via client-side checkboxes
2. **Bulk processing** - Single API call handles multiple charges
3. **Reference tracking** - Charges link back to generated invoices via `is_invoiced` flags
4. **Validation** - Prevents modification/deletion of invoiced charges

Example API pattern:
```python
@frappe.whitelist()
def create_sales_invoice_with_rows(docname, row_names):
    # Parse selected rows, create invoice, update references
```

## Development Conventions

### Frappe Integration
- **Custom Fields**: Extensively uses ERPNext doctypes (Sales Invoice, Purchase Invoice) with custom fields prefixed `custom_`
- **Fixtures**: All custom fields, roles, workflows managed via `fixtures` in `hooks.py`
- **Doc Events**: Uses `doc_events` for validation hooks on Trip charges

### JavaScript Patterns
- **Client Scripts**: Located in `public/js/` directory
- **Calculation Logic**: Real-time total calculations in form scripts (see `quotation.js`)
- **Form Extensions**: Use `frappe.ui.form.on()` for custom behaviors

### API Design
- **Whitelisted Methods**: All API endpoints use `@frappe.whitelist()` decorator
- **Error Handling**: Consistent `try/catch` with `frappe.log_error()` and user-friendly messages
- **JSON Parsing**: Always handle both string and object inputs with `frappe.parse_json()`

### Report Architecture
- **Script Reports**: All reports use Python execution with standardized column/data structure
- **Export Utilities**: Common PDF/Excel export functions in `api.py` with template rendering
- **Template System**: HTML templates in `templates/` for PDF generation

## Key Workflows

### Clearing Job Lifecycle
1. **Creation** → **Charges Entry** → **Invoice Generation** → **Completion**
2. Supports both sales (customer) and purchase (supplier) invoice creation
3. Auto-calculation of revenue/cost/profit in multiple currencies

### Trip Management
1. **Planning** → **Execution** → **Invoicing** → **Settlement**
2. Fuel allocation with stock entries
3. Expense management via journal entries
4. Bulk invoice creation for efficiency

### Charge Management
- **Revenue Charges**: Customer billing (sales invoices)
- **Cost Charges**: Supplier billing (purchase invoices)  
- **Fuel Charges**: Stock entry creation for inventory tracking
- **Other Costs**: Journal entry creation for expense booking

## Critical Business Rules

### Invoice Protection
Once charges are invoiced (`is_invoiced=1`), they cannot be modified or deleted. This is enforced at:
- Document validation level
- Child table `before_delete` hooks
- Form-level validation

### Currency Handling
- Multi-currency support with conversion rates
- Base currency calculations for company reporting
- Automatic currency detection from company defaults

### Workflow Integration
- Uses Frappe workflows for document state management
- Status-based field updates (e.g., `completed_on` auto-setting)
- Role-based permissions via fixtures

## File Organization Tips

### Finding Business Logic
- **Core calculations**: Check `{doctype}.py` files in respective service modules
- **API endpoints**: Look in main `api.py` file
- **Client behavior**: Check `public/js/` directory
- **Report logic**: Navigate to `{service}/report/{report_name}/{report_name}.py`

### Common Utilities
- **Fuel calculations**: `utils/fuel_utils.py`
- **Storage/DND calculations**: `utils/dnd_storage_days.py`
- **Export functions**: Main `api.py` file

### Template Locations
- **PDF templates**: `templates/*.html`
- **Print formats**: `{service}/print_format/`
- **Workspace configs**: `{service}/workspace/`

## Testing & Development

### Environment Setup
This is a Frappe app that requires:
1. Frappe framework installation
2. ERPNext as base app
3. Standard Frappe development workflow

### Common Commands
```bash
# Install in development mode
bench get-app freightmas
bench install-app freightmas

# Development server
bench start

# Run migrations
bench migrate
```

### Debugging Tips
- Use `frappe.log_error()` for server-side debugging
- Check browser console for client-side issues  
- Use `bench console` for testing server-side code
- Monitor background jobs via Frappe's job queue

## Integration Points

### ERPNext Dependencies
- Heavily extends Customer, Supplier, Item, Sales Invoice, Purchase Invoice
- Uses Company, Currency, Stock Entry for business operations
- Integrates with Journal Entry for expense management

### External Systems
- No direct external API integrations identified
- Designed for manual data entry and internal workflow management
- Export capabilities for external reporting needs