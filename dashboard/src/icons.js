import {
	LayoutDashboard,
	Ship,
	ClipboardCheck,
	Signpost,
	Route,
	Truck,
	Warehouse,
	Receipt,
} from "@lucide/vue";

// Maps each nav item's `icon` key (see router.js NAV_ITEMS) to a lucide
// component. Kept separate from router.js so both the sidebar and the
// "coming soon" placeholder can share one source of truth.
export const NAV_ICONS = {
	overview: LayoutDashboard,
	forwarding: Ship,
	clearing: ClipboardCheck,
	"border-clearing": Signpost,
	"road-freight": Route,
	trucking: Truck,
	warehouse: Warehouse,
	invoicing: Receipt,
};
