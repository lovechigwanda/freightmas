import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.supplier.dashboard");

export const api = {
	getOverview: () => client.call("get_overview"),
};
