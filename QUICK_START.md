# FreightMas - Quick Start Guide

## 🚀 Get FreightMas Running in 5 Minutes

This guide gets you up and running with FreightMas as quickly as possible.

---

## Prerequisites

- Ubuntu/Debian Linux (or WSL2 on Windows)
- At least 4GB RAM
- 10GB free disk space

---

## Option 1: Fresh Installation (Recommended for New Users)

### Step 1: Install Frappe Bench

```bash
# Install dependencies
sudo apt update && sudo apt install -y python3-pip python3-dev python3-venv \
    nodejs npm mariadb-server redis-server git

# Install bench
sudo pip3 install frappe-bench
```

### Step 2: Initialize Bench

```bash
bench init frappe-bench --frappe-branch version-15
cd frappe-bench
```

### Step 3: Create Site

```bash
bench new-site mysite.local
# Enter MySQL root password and admin password when prompted
```

### Step 4: Install Apps

```bash
# Install ERPNext
bench get-app erpnext --branch version-15
bench --site mysite.local install-app erpnext

# Install FreightMas
bench get-app https://github.com/lovechigwanda/freightmas.git
bench --site mysite.local install-app freightmas

# Complete setup
bench --site mysite.local migrate
bench build --app freightmas
bench restart
```

### Step 5: Start and Access

```bash
bench start
```

Open browser: `http://mysite.local:8000`
- Username: `Administrator`
- Password: (password you set in Step 3)

---

## Option 2: Add to Existing Bench

If you already have Frappe/ERPNext installed:

```bash
cd ~/frappe-bench

# Get and install FreightMas
bench get-app https://github.com/lovechigwanda/freightmas.git
bench --site [your-site] install-app freightmas

# Complete setup
bench --site [your-site] migrate
bench build --app freightmas
bench restart
```

---

## Option 3: Clone for Development

To contribute or customize FreightMas:

```bash
# Fork the repo on GitHub first, then:

cd ~/frappe-bench/apps
git clone https://github.com/YOUR-USERNAME/freightmas.git
cd freightmas
git remote add upstream https://github.com/lovechigwanda/freightmas.git

# Install
cd ~/frappe-bench
bench --site mysite.local install-app freightmas
bench --site mysite.local clear-cache
bench build --app freightmas
bench restart
```

---

## Verify Installation

### Check Apps

```bash
bench --site mysite.local list-apps
```

You should see: `frappe`, `erpnext`, `freightmas`

### Access FreightMas Modules

1. Login to your site
2. Use the search bar (Ctrl+K or Cmd+K)
3. Search for:
   - Port Clearing Service
   - Trucking Service
   - Forwarding Service
   - Road Freight Service

If you see these workspaces, FreightMas is installed correctly! 🎉

---

## Quick Troubleshooting

### App not appearing?

```bash
bench --site mysite.local clear-cache
bench build --app freightmas
bench restart
```

### Build errors?

```bash
bench setup requirements
bench build
```

### Database errors?

```bash
bench --site mysite.local migrate --skip-search-index
```

### Start fresh?

```bash
bench --site mysite.local reinstall
bench --site mysite.local install-app erpnext
bench --site mysite.local install-app freightmas
```

---

## Next Steps

1. **Read the full documentation**: Check `CLONING_GUIDE.md` for detailed setup
2. **Explore modules**: Navigate through each service workspace
3. **Check guides**: Review service-specific documentation in module folders
4. **Set up demo data**: Create test customers, suppliers, and jobs

---

## Need Help?

- **Full Setup Guide**: See `CLONING_GUIDE.md`
- **Issues**: https://github.com/lovechigwanda/freightmas/issues
- **Frappe Community**: https://discuss.frappe.io

---

**Happy FreightMas-ing! 🚚📦**
