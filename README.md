# FreightMas

Comprehensive Freight and Logistics Management System built on Frappe/ERPNext

## 📋 Overview

FreightMas is a comprehensive Frappe application for freight and logistics management. It manages four core service domains:
- **Port Clearing** - Import/export clearing operations
- **Trucking** - Fleet and trip management
- **Forwarding** - Freight forwarding services
- **Road Freight** - Road transport services

## 🔧 Prerequisites

Before cloning and setting up FreightMas, ensure you have the following installed:

- **Python**: 3.10 or higher
- **Node.js**: 18 or higher
- **MariaDB**: 10.6 or higher
- **Redis**: Latest stable version
- **Frappe Framework**: Version 15.0 or compatible
- **ERPNext**: Latest version compatible with Frappe 15

## 🚀 Quick Start - Cloning the Repository

### Step 1: Clone FreightMas Repository

If you already have a Frappe bench set up, clone FreightMas as a Frappe app:

```bash
# Navigate to your frappe-bench directory
cd ~/frappe-bench

# Clone the FreightMas app
bench get-app https://github.com/lovechigwanda/freightmas.git
```

### Step 2: Install FreightMas on Your Site

```bash
# Install the app on your site
bench --site [your-site-name] install-app freightmas

# Example:
# bench --site mysite.local install-app freightmas
```

### Step 3: Run Migrations and Build

```bash
# Run database migrations
bench --site [your-site-name] migrate

# Clear cache
bench --site [your-site-name] clear-cache

# Build assets
bench build --app freightmas

# Restart bench
bench restart
```

## 🆕 Fresh Installation (No Existing Bench)

If you don't have a Frappe bench setup, follow these steps:

### Step 1: Install Frappe Bench

```bash
# Install bench CLI
pip3 install frappe-bench

# Create a new bench
bench init frappe-bench --frappe-branch version-15

# Navigate to bench directory
cd frappe-bench
```

### Step 2: Create a New Site

```bash
# Create a new site
bench new-site [your-site-name]

# Example:
# bench new-site mysite.local

# You will be prompted to enter:
# - MySQL root password
# - Administrator password for your site
```

### Step 3: Install ERPNext

```bash
# Get ERPNext app
bench get-app erpnext --branch version-15

# Install ERPNext on your site
bench --site [your-site-name] install-app erpnext
```

### Step 4: Get and Install FreightMas

```bash
# Clone FreightMas
bench get-app https://github.com/lovechigwanda/freightmas.git

# Install FreightMas
bench --site [your-site-name] install-app freightmas

# Build and restart
bench build --app freightmas
bench restart
```

### Step 5: Start the Development Server

```bash
# Start bench in development mode
bench start
```

Access your site at: `http://[your-site-name]:8000`

## 🛠️ Development Setup

### For Development Contributions

1. **Fork the Repository** on GitHub

2. **Clone Your Fork**:
```bash
cd ~/frappe-bench/apps
git clone https://github.com/[your-username]/freightmas.git
cd freightmas
```

3. **Add Upstream Remote**:
```bash
git remote add upstream https://github.com/lovechigwanda/freightmas.git
```

4. **Create a Development Branch**:
```bash
git checkout -b feature/your-feature-name
```

5. **Make Your Changes** and test thoroughly

6. **Run in Development Mode**:
```bash
# From bench directory
bench --site [your-site-name] clear-cache
bench build --app freightmas
bench restart
```

## 📦 Module Structure

FreightMas follows a modular architecture:

```
freightmas/
├── clearing_service/      # Port clearing operations
├── trucking_service/      # Trucking and fleet management
├── forwarding_service/    # Freight forwarding
├── road_freight_service/  # Road freight operations
├── warehouse_service/     # Warehouse management
├── utils/                 # Shared utilities
├── public/                # Static assets (JS, CSS)
├── templates/             # HTML templates
└── fixtures/              # Initial data and configurations
```

## 🔑 Key Features

- **Multi-Service Management**: Handle clearing, trucking, forwarding, and road freight
- **Invoice Generation**: Automated invoice creation from charges
- **Multi-Currency Support**: Handle transactions in multiple currencies
- **Comprehensive Reporting**: Built-in reports for all services
- **Template System**: Reusable charge templates
- **Workflow Integration**: Status-based document workflows

## 📚 Documentation

- **User Guides**: See individual service documentation in respective module folders
- **Job Order Guide**: `freightmas/forwarding_service/doctype/job_order/JOB_ORDER_GUIDE.md`
- **Warehouse Setup**: `freightmas/warehouse_service/SETUP_GUIDE.md`
- **Report Creation**: `freightmas/docs/REPORT_CREATION_GUIDE.md`

## 🐛 Troubleshooting

### Common Issues

**Issue**: App not showing after installation
```bash
# Solution: Clear cache and rebuild
bench --site [your-site-name] clear-cache
bench build --app freightmas
bench restart
```

**Issue**: Database migration errors
```bash
# Solution: Run migrate with force flag
bench --site [your-site-name] migrate --skip-search-index
```

**Issue**: Permission errors
```bash
# Solution: Set proper permissions
bench setup requirements
sudo chmod -R 755 ~/frappe-bench
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - See `license.txt` for details

## 👥 Authors

**Zvomaita Technologies (Pvt) Ltd**
- Email: info@zvomaita.co.zw

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in the `docs/` folder
- Review service-specific guides in module directories

## 🔄 Keeping Your Clone Updated

```bash
# Navigate to the app directory
cd ~/frappe-bench/apps/freightmas

# Fetch latest changes from upstream
git fetch upstream

# Merge changes into your local branch
git merge upstream/main

# Update bench
cd ~/frappe-bench
bench --site [your-site-name] migrate
bench build --app freightmas
bench restart
```

---

**Happy Freight Management! 🚚📦**