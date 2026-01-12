# Contributing to FreightMas

Thank you for your interest in contributing to FreightMas! This document provides guidelines and instructions for contributing to the project.

## 🤝 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/lovechigwanda/freightmas/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Your environment details (OS, Frappe version, etc.)

### Suggesting Enhancements

1. Check existing [Issues](https://github.com/lovechigwanda/freightmas/issues) for similar suggestions
2. Create a new issue with:
   - Clear description of the enhancement
   - Use cases and benefits
   - Possible implementation approach

### Code Contributions

## 🔄 Fork and Clone Workflow

### 1. Fork the Repository

1. Visit https://github.com/lovechigwanda/freightmas
2. Click the "Fork" button (top right)
3. This creates a copy under your GitHub account

### 2. Clone Your Fork

```bash
# Navigate to your bench apps directory
cd ~/frappe-bench/apps

# Clone your fork (replace YOUR-USERNAME)
git clone https://github.com/YOUR-USERNAME/freightmas.git

# Navigate into the directory
cd freightmas

# Add the original repository as 'upstream'
git remote add upstream https://github.com/lovechigwanda/freightmas.git

# Verify remotes
git remote -v
# Should show:
# origin    https://github.com/YOUR-USERNAME/freightmas.git (fetch)
# origin    https://github.com/YOUR-USERNAME/freightmas.git (push)
# upstream  https://github.com/lovechigwanda/freightmas.git (fetch)
# upstream  https://github.com/lovechigwanda/freightmas.git (push)
```

### 3. Install for Development

```bash
# Navigate to bench directory
cd ~/frappe-bench

# Install the app on your development site
bench --site mysite.local install-app freightmas

# Enable developer mode
bench --site mysite.local set-config developer_mode 1

# Set up watch for automatic rebuild (optional)
bench --site mysite.local set-config auto_reload 1
```

## 💻 Development Workflow

### Create a Feature Branch

```bash
cd ~/frappe-bench/apps/freightmas

# Make sure you're on main and up to date
git checkout main
git pull upstream main

# Create a new feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### Make Your Changes

1. Write clean, readable code
2. Follow existing code style and conventions
3. Add comments for complex logic
4. Update documentation if needed

### Test Your Changes

```bash
# Clear cache
bench --site mysite.local clear-cache

# Rebuild assets
bench build --app freightmas

# Restart bench
bench restart

# Test manually in the UI
# Or run automated tests if available
```

### Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a clear message
git commit -m "Add feature: brief description"

# Good commit message examples:
# "Fix invoice generation bug in clearing service"
# "Add bulk update functionality to trip management"
# "Update documentation for warehouse setup"
```

### Push to Your Fork

```bash
# Push your feature branch to your fork
git push origin feature/your-feature-name
```

### Create a Pull Request

1. Go to your fork on GitHub
2. Click "Compare & pull request" button
3. Fill in the PR template:
   - **Title**: Clear, descriptive title
   - **Description**: What changes were made and why
   - **Testing**: How you tested the changes
   - **Screenshots**: If UI changes were made
4. Submit the pull request

## 📝 Coding Standards

### Python Code

- Follow [PEP 8](https://pep8.org/) style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Use type hints where appropriate

```python
def calculate_total_charges(charges: list, currency: str) -> float:
    """
    Calculate total amount from list of charges.
    
    Args:
        charges: List of charge dictionaries
        currency: Currency code for conversion
        
    Returns:
        Total amount as float
    """
    total = 0.0
    for charge in charges:
        total += float(charge.get('amount', 0))
    return total
```

### JavaScript Code

- Use ES6+ syntax
- Follow existing code patterns in the codebase
- Add comments for complex logic
- Use meaningful variable names

```javascript
// Good
const calculateTotalRevenue = (charges) => {
    return charges.reduce((total, charge) => total + charge.amount, 0);
};

// Avoid
const calc = (c) => {
    let t = 0;
    for(let i = 0; i < c.length; i++) t += c[i].a;
    return t;
};
```

### Frappe-Specific Guidelines

1. **DocType Naming**: Use PascalCase (e.g., `ClearingJob`, `TripRevenue`)
2. **Field Naming**: Use snake_case (e.g., `customer_name`, `total_amount`)
3. **Whitelist Methods**: Always use `@frappe.whitelist()` for API methods
4. **Error Handling**: Use `frappe.throw()` for user-facing errors
5. **Validation**: Add validation in Python controllers, not just client-side

### Documentation

- Update README.md if adding major features
- Add docstrings to new functions
- Create or update guides for new modules
- Include examples where helpful

## 🔍 Code Review Process

1. Maintainers will review your PR
2. They may request changes or ask questions
3. Make requested changes in your feature branch
4. Push updates (they'll automatically appear in the PR)
5. Once approved, maintainers will merge your PR

## 🔄 Keeping Your Fork Updated

### Sync with Upstream Regularly

```bash
cd ~/frappe-bench/apps/freightmas

# Fetch upstream changes
git fetch upstream

# Switch to main branch
git checkout main

# Merge upstream changes
git merge upstream/main

# Push to your fork
git push origin main
```

### Rebase Your Feature Branch

```bash
# Switch to your feature branch
git checkout feature/your-feature-name

# Rebase on latest main
git rebase main

# If conflicts, resolve them and:
git add .
git rebase --continue

# Force push to your fork (be careful!)
git push origin feature/your-feature-name --force
```

## 🧪 Testing Guidelines

### Manual Testing Checklist

Before submitting a PR, ensure:

- [ ] Feature works as expected in the UI
- [ ] No console errors in browser
- [ ] No Python errors in terminal
- [ ] Existing functionality still works
- [ ] Works with different user permissions
- [ ] Tested with sample data
- [ ] Migration runs successfully on a fresh site

### Test Data

Create test data to verify your changes:

```bash
# Create a test site for clean testing
bench new-site test.local
bench --site test.local install-app erpnext
bench --site test.local install-app freightmas

# Test your changes
# ...

# Drop test site when done
bench drop-site test.local
```

## 📋 PR Checklist

Before submitting, ensure:

- [ ] Code follows project style guidelines
- [ ] All tests pass (if applicable)
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] No unnecessary files committed (check .gitignore)
- [ ] Changes are minimal and focused
- [ ] Screenshots included for UI changes
- [ ] Breaking changes are documented

## 🚫 What NOT to Do

- Don't commit directly to main branch
- Don't commit sensitive data (passwords, API keys)
- Don't commit compiled files (pyc, node_modules)
- Don't make unrelated changes in one PR
- Don't copy code without proper attribution
- Don't submit PRs without testing

## 🏷️ Branch Naming Convention

Use descriptive branch names:

- `feature/add-trip-bulk-update` - New features
- `fix/invoice-calculation-error` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/optimize-query` - Code refactoring
- `test/add-clearing-job-tests` - Test additions

## 📞 Getting Help

- **Questions**: Open a discussion or issue on GitHub
- **Frappe Questions**: Check [Frappe Forum](https://discuss.frappe.io)
- **ERPNext Questions**: Check [ERPNext Forum](https://discuss.erpnext.com)

## 📜 License

By contributing to FreightMas, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to FreightMas! Your efforts help make freight management better for everyone. 🚚📦

