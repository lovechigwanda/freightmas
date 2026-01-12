# FreightMas Repository Cloning and Setup Guide

This guide provides detailed instructions for cloning and setting up the FreightMas repository in different scenarios.

## Table of Contents
1. [Quick Clone for Existing Bench](#quick-clone-for-existing-bench)
2. [Complete Setup from Scratch](#complete-setup-from-scratch)
3. [Forking and Contributing](#forking-and-contributing)
4. [Production Deployment](#production-deployment)
5. [Docker Setup](#docker-setup)
6. [Common Issues](#common-issues)

---

## Quick Clone for Existing Bench

If you already have a working Frappe bench with ERPNext installed:

### Method 1: Using bench get-app (Recommended)

```bash
# Navigate to your bench directory
cd ~/frappe-bench

# Get the FreightMas app
bench get-app https://github.com/lovechigwanda/freightmas.git

# Install on your site
bench --site mysite.local install-app freightmas

# Migrate and restart
bench --site mysite.local migrate
bench --site mysite.local clear-cache
bench build --app freightmas
bench restart
```

### Method 2: Manual Git Clone

```bash
# Navigate to apps directory
cd ~/frappe-bench/apps

# Clone the repository
git clone https://github.com/lovechigwanda/freightmas.git

# Navigate back to bench
cd ..

# Install the app
bench --site mysite.local install-app freightmas

# Complete setup
bench --site mysite.local migrate
bench build --app freightmas
bench restart
```

---

## Complete Setup from Scratch

### Prerequisites Installation

#### On Ubuntu/Debian:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3-dev python3-pip python3-venv \
    nodejs npm \
    mariadb-server mariadb-client \
    redis-server \
    git \
    libmysqlclient-dev \
    xvfb libfontconfig wkhtmltopdf

# Secure MariaDB installation
sudo mysql_secure_installation

# Install Node.js 18 (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install yarn
sudo npm install -g yarn
```

### Install Frappe Bench

```bash
# Install bench via pip
sudo pip3 install frappe-bench

# Verify installation
bench --version
```

### Initialize a New Bench

```bash
# Create bench with Frappe version 15
bench init frappe-bench --frappe-branch version-15

# Navigate to bench directory
cd frappe-bench
```

### Create and Configure Site

```bash
# Create a new site
bench new-site mysite.local

# You'll be prompted for:
# - MySQL root password
# - Administrator password (remember this!)

# Set the site as the current site (optional but recommended)
bench use mysite.local
```

### Install ERPNext

```bash
# Get ERPNext app
bench get-app erpnext --branch version-15

# Install ERPNext on site
bench --site mysite.local install-app erpnext

# This may take a few minutes
```

### Install FreightMas

```bash
# Get FreightMas app
bench get-app https://github.com/lovechigwanda/freightmas.git

# Install FreightMas
bench --site mysite.local install-app freightmas

# Run migrations
bench --site mysite.local migrate

# Clear cache
bench --site mysite.local clear-cache

# Build assets
bench build

# Restart
bench restart
```

### Start Development Server

```bash
# Start in development mode
bench start

# Access your site at:
# http://mysite.local:8000
# Default credentials:
# Username: Administrator
# Password: (the password you set during site creation)
```

### Enable Developer Mode (For Development)

```bash
# Enable developer mode
bench --site mysite.local set-config developer_mode 1

# Disable CSRF (for API testing, development only!)
bench --site mysite.local set-config ignore_csrf 1

# Restart
bench restart
```

---

## Forking and Contributing

### Fork the Repository

1. Go to https://github.com/lovechigwanda/freightmas
2. Click the "Fork" button in the top-right corner
3. This creates a copy under your GitHub account

### Clone Your Fork

```bash
cd ~/frappe-bench/apps

# Clone your fork (replace YOUR-USERNAME)
git clone https://github.com/YOUR-USERNAME/freightmas.git

cd freightmas

# Add upstream remote
git remote add upstream https://github.com/lovechigwanda/freightmas.git

# Verify remotes
git remote -v
```

### Set Up Development Workflow

```bash
# Create a new feature branch
git checkout -b feature/my-new-feature

# Make your changes...

# Install for development (if not already installed)
cd ~/frappe-bench
bench --site mysite.local install-app freightmas

# Test your changes
bench --site mysite.local clear-cache
bench build --app freightmas
bench restart
```

### Sync with Upstream

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

### Submit a Pull Request

1. Push your feature branch to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```

2. Go to your fork on GitHub
3. Click "Compare & pull request"
4. Fill in the PR description
5. Submit the pull request

---

## Production Deployment

### Using Bench Production Setup

```bash
# Setup production (run as root or with sudo)
sudo bench setup production [your-user]

# Example:
# sudo bench setup production frappe

# Enable scheduler
bench --site mysite.local enable-scheduler

# Setup SSL (optional, requires domain)
sudo bench setup lets-encrypt mysite.com

# Restart services
sudo supervisorctl restart all
sudo service nginx reload
```

### Manual Production Configuration

```bash
# Create production config
bench setup nginx
bench setup supervisor

# Restart services
sudo ln -s `pwd`/config/supervisor.conf /etc/supervisor/conf.d/frappe-bench.conf
sudo ln -s `pwd`/config/nginx.conf /etc/nginx/conf.d/frappe-bench.conf

sudo supervisorctl reread
sudo supervisorctl update
sudo service nginx reload
```

---

## Docker Setup

### Using Official Frappe Docker

```bash
# Clone frappe_docker repository
git clone https://github.com/frappe/frappe_docker.git
cd frappe_docker

# Copy example environment
cp example.env .env

# Edit .env file to configure your setup
nano .env

# Start containers
docker compose -f compose.yaml \
    -f overrides/compose.mariadb.yaml \
    -f overrides/compose.redis.yaml \
    -f overrides/compose.https.yaml up -d

# Create site
docker compose exec backend bench new-site mysite.local --install-app erpnext

# Get FreightMas app in container
docker compose exec backend bench get-app https://github.com/lovechigwanda/freightmas.git

# Install FreightMas
docker compose exec backend bench --site mysite.local install-app freightmas
```

### Custom Dockerfile for FreightMas

Create a `Dockerfile.freightmas`:

```dockerfile
FROM frappe/erpnext:v15

USER frappe

# Clone FreightMas
RUN bench get-app https://github.com/lovechigwanda/freightmas.git

# Install FreightMas on site
RUN bench --site mysite.local install-app freightmas

USER root

# Final setup
RUN bench setup requirements
```

---

## Common Issues and Solutions

### Issue: Permission Denied

```bash
# Fix permissions
cd ~/frappe-bench
sudo chown -R $USER:$USER .
chmod -R 755 .
```

### Issue: Port Already in Use

```bash
# Change default port
bench set-config http_port 8001

# Or kill process using port 8000
sudo lsof -ti:8000 | xargs kill -9
```

### Issue: MariaDB Connection Error

```bash
# Check MariaDB status
sudo systemctl status mariadb

# Start MariaDB if stopped
sudo systemctl start mariadb

# Reset site database
bench --site mysite.local reinstall
```

### Issue: Redis Connection Error

```bash
# Check Redis status
sudo systemctl status redis

# Start Redis if stopped
sudo systemctl start redis

# Or install if missing
sudo apt install redis-server
```

### Issue: Build Failures

```bash
# Clear node_modules and rebuild
cd ~/frappe-bench
rm -rf node_modules
rm -rf apps/*/node_modules

# Reinstall dependencies
bench setup requirements

# Rebuild
bench build
```

### Issue: Migration Errors

```bash
# Run migrate with verbose output
bench --site mysite.local migrate --skip-search-index

# If persistent, try:
bench --site mysite.local migrate --rebuild-indexes
```

### Issue: App Not Showing After Install

```bash
# Ensure app is installed
bench --site mysite.local list-apps

# If not listed, install again
bench --site mysite.local install-app freightmas

# Clear all caches
bench --site mysite.local clear-cache
bench --site mysite.local clear-website-cache

# Rebuild
bench build --app freightmas
bench restart
```

---

## Verifying Installation

### Check Installed Apps

```bash
bench --site mysite.local list-apps
```

Expected output should include:
- frappe
- erpnext
- freightmas

### Access FreightMas Modules

1. Login to your site
2. Go to "Awesome Bar" (search) and type:
   - "Port Clearing Service"
   - "Trucking Service"
   - "Forwarding Service"
   - "Road Freight Service"

3. You should see the FreightMas workspaces

### Test Basic Functionality

```bash
# Run bench console
bench --site mysite.local console

# Test import
import frappe
frappe.get_installed_apps()

# Should show 'freightmas' in the list
```

---

## Additional Resources

- **Frappe Framework Docs**: https://frappeframework.com/docs
- **ERPNext Docs**: https://docs.erpnext.com
- **Bench CLI**: https://github.com/frappe/bench
- **FreightMas Issues**: https://github.com/lovechigwanda/freightmas/issues

---

## Support and Community

For help with FreightMas:
- Open an issue on GitHub: https://github.com/lovechigwanda/freightmas/issues
- Check existing documentation in the repository
- Review module-specific guides

For general Frappe/ERPNext questions:
- Frappe Forum: https://discuss.frappe.io
- ERPNext Forum: https://discuss.erpnext.com

---

**Last Updated**: January 2026

**Maintained by**: Zvomaita Technologies (Pvt) Ltd
