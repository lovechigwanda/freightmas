#!/bin/bash

###############################################################################
# FreightMas Clone and Setup Script
# 
# This script helps you clone and set up FreightMas repository
# in your Frappe bench environment.
#
# Usage: ./clone_freightmas.sh [options]
# Options:
#   --site SITENAME    Specify site name (default: interactive prompt)
#   --bench-path PATH  Specify bench path (default: ~/frappe-bench)
#   --dev              Setup for development (fork workflow)
#   --help             Show this help message
###############################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BENCH_PATH="$HOME/frappe-bench"
SITE_NAME=""
DEV_MODE=false
GITHUB_REPO="https://github.com/lovechigwanda/freightmas.git"

# Functions
print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  FreightMas Clone and Setup Script${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_step() {
    echo -e "${BLUE}▸ $1${NC}"
}

show_help() {
    echo "FreightMas Clone and Setup Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --site SITENAME    Specify site name (default: interactive prompt)"
    echo "  --bench-path PATH  Specify bench path (default: ~/frappe-bench)"
    echo "  --dev              Setup for development (fork workflow)"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --site mysite.local"
    echo "  $0 --bench-path /home/user/frappe-bench --site mysite.local"
    echo "  $0 --dev --site development.local"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --site)
            SITE_NAME="$2"
            shift 2
            ;;
        --bench-path)
            BENCH_PATH="$2"
            shift 2
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main script
print_header

# Check if bench exists
if [ ! -d "$BENCH_PATH" ]; then
    print_error "Bench directory not found at: $BENCH_PATH"
    print_info "Please specify correct bench path using --bench-path option"
    exit 1
fi

print_success "Found bench at: $BENCH_PATH"

# Get site name if not provided
if [ -z "$SITE_NAME" ]; then
    echo ""
    print_info "Available sites:"
    ls -1 "$BENCH_PATH/sites" | grep -v "apps.txt" | grep -v "assets" | grep -v "common_site_config.json"
    echo ""
    read -p "Enter site name: " SITE_NAME
fi

# Validate site exists
if [ ! -d "$BENCH_PATH/sites/$SITE_NAME" ]; then
    print_error "Site '$SITE_NAME' not found in $BENCH_PATH/sites/"
    print_info "Create a new site with: bench new-site $SITE_NAME"
    exit 1
fi

print_success "Using site: $SITE_NAME"

# Navigate to bench directory
cd "$BENCH_PATH"

# Check if FreightMas already exists
if [ -d "apps/freightmas" ]; then
    print_info "FreightMas app already exists in apps directory"
    read -p "Do you want to reinstall? (y/n): " REINSTALL
    if [[ $REINSTALL =~ ^[Yy]$ ]]; then
        print_step "Removing existing FreightMas app..."
        rm -rf apps/freightmas
        print_success "Removed existing FreightMas"
    else
        print_info "Keeping existing installation. Skipping clone."
        SKIP_CLONE=true
    fi
fi

# Clone or get app
if [ "$SKIP_CLONE" != true ]; then
    echo ""
    print_step "Cloning FreightMas repository..."
    
    if [ "$DEV_MODE" = true ]; then
        print_info "Development mode: Please fork the repository first on GitHub"
        read -p "Enter your GitHub username: " GITHUB_USER
        
        if [ -z "$GITHUB_USER" ]; then
            print_error "GitHub username is required for development mode"
            exit 1
        fi
        
        cd apps
        print_step "Cloning from your fork..."
        git clone "https://github.com/$GITHUB_USER/freightmas.git"
        
        cd freightmas
        print_step "Adding upstream remote..."
        git remote add upstream "$GITHUB_REPO"
        git fetch upstream
        
        print_success "Cloned from fork and added upstream remote"
        cd "$BENCH_PATH"
    else
        print_step "Getting app via bench..."
        bench get-app freightmas
        print_success "FreightMas app cloned successfully"
    fi
fi

# Install app on site
echo ""
print_step "Installing FreightMas on site: $SITE_NAME"

# Check if already installed
if bench --site "$SITE_NAME" list-apps | grep -q "freightmas"; then
    print_info "FreightMas is already installed on this site"
    read -p "Do you want to reinstall? (y/n): " REINSTALL_APP
    if [[ ! $REINSTALL_APP =~ ^[Yy]$ ]]; then
        print_info "Skipping app installation"
        SKIP_INSTALL=true
    fi
fi

if [ "$SKIP_INSTALL" != true ]; then
    bench --site "$SITE_NAME" install-app freightmas
    print_success "FreightMas installed successfully"
fi

# Run migrations
echo ""
print_step "Running database migrations..."
bench --site "$SITE_NAME" migrate
print_success "Migrations completed"

# Clear cache
print_step "Clearing cache..."
bench --site "$SITE_NAME" clear-cache
print_success "Cache cleared"

# Build assets
print_step "Building assets..."
bench build --app freightmas
print_success "Assets built"

# Set developer mode if dev flag is set
if [ "$DEV_MODE" = true ]; then
    print_step "Enabling developer mode..."
    bench --site "$SITE_NAME" set-config developer_mode 1
    print_success "Developer mode enabled"
fi

# Restart bench
print_step "Restarting bench..."
bench restart
print_success "Bench restarted"

# Final message
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  FreightMas Setup Complete! 🎉${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
print_info "Next steps:"
echo "  1. Start bench: cd $BENCH_PATH && bench start"
echo "  2. Access site: http://$SITE_NAME:8000"
echo "  3. Login with Administrator credentials"
echo "  4. Search for 'Port Clearing Service' to access FreightMas"
echo ""

if [ "$DEV_MODE" = true ]; then
    print_info "Development workflow:"
    echo "  • Create feature branch: cd apps/freightmas && git checkout -b feature/my-feature"
    echo "  • Make changes and test"
    echo "  • Push to fork: git push origin feature/my-feature"
    echo "  • Create pull request on GitHub"
    echo ""
fi

print_info "Documentation:"
echo "  • Quick Start: $BENCH_PATH/apps/freightmas/QUICK_START.md"
echo "  • Full Guide: $BENCH_PATH/apps/freightmas/CLONING_GUIDE.md"
echo "  • README: $BENCH_PATH/apps/freightmas/README.md"
echo ""

print_success "Setup completed successfully!"
