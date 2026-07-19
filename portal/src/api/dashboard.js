import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.api.dashboard");

export const api = {
	getOverview: () => client.call("get_overview"),
};
