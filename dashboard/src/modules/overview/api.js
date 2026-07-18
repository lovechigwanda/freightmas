// API client for the Command Center shell + top-level Overview.
// Backed by the freightmas_command_center Python module, which currently
// proxies branding + overview data from the Forwarding module (the only
// module with a working dashboard so far) but is the right home for
// cross-module aggregation as Clearing/Trucking/etc. are added.
import { createApiClient } from "../../api/core";

const client = createApiClient("freightmas.freightmas.page.freightmas_command_center.freightmas_command_center");

export const api = {
	getBranding: () => client.call("get_branding"),
	getOverview: () => client.call("get_overview"),
	// Cross-module executive rollup (KPIs, module scorecards, invoicing, cash,
	// combined trend, top customers).
	getExecutiveOverview: (params) => client.call("get_executive_overview", params),
};
