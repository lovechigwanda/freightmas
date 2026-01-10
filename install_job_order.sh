#!/bin/bash

# Job Order Installation Script
# Run this script to install the Job Order DocType

echo "======================================"
echo "Job Order Installation"
echo "======================================"
echo ""

# Get the site name
read -p "Enter your site name (e.g., mysite.local): " SITE_NAME

if [ -z "$SITE_NAME" ]; then
    echo "Error: Site name is required"
    exit 1
fi

echo ""
echo "Installing Job Order for site: $SITE_NAME"
echo ""

# Navigate to bench directory
BENCH_DIR="/home/simbarashe/frappe-bench"
cd "$BENCH_DIR" || exit 1

echo "Step 1: Running database migration..."
bench --site "$SITE_NAME" migrate

echo ""
echo "Step 2: Clearing cache..."
bench --site "$SITE_NAME" clear-cache

echo ""
echo "Step 3: Importing fixtures (workspace configuration)..."
bench --site "$SITE_NAME" import-doc

echo ""
echo "Step 4: Building assets..."
bench build --app freightmas

echo ""
echo "Step 5: Restarting bench..."
bench restart

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "Next Steps:"
echo "1. Login to your site"
echo "2. Go to an Accepted Forwarding Quotation"
echo "3. Click 'Create → Create Job Order'"
echo "4. Test the complete workflow"
echo ""
echo "Documentation:"
echo "- User Guide: apps/freightmas/freightmas/forwarding_service/doctype/job_order/JOB_ORDER_GUIDE.md"
echo "- Implementation: apps/freightmas/freightmas/JOB_ORDER_IMPLEMENTATION.md"
echo ""
echo "Support: Check the documentation files for troubleshooting"
echo ""
