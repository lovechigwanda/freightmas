import { LayoutDashboard, Truck, Receipt, User } from "@lucide/vue";

// Maps each nav item's `icon` key (see router.js NAV_ITEMS) to a lucide
// component - same indirection pattern as portal/src/icons.js.
export const NAV_ICONS = {
	dashboard: LayoutDashboard,
	jobs: Truck,
	invoices: Receipt,
	profile: User,
};
