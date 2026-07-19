import { LayoutDashboard, Ship, Receipt, Wallet, User } from "@lucide/vue";

// Maps each nav item's `icon` key (see router.js NAV_ITEMS) to a lucide
// component - same indirection pattern as dashboard/src/icons.js.
export const NAV_ICONS = {
	dashboard: LayoutDashboard,
	shipments: Ship,
	invoices: Receipt,
	payments: Wallet,
	profile: User,
};
