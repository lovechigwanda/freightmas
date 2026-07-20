import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.supplier.profile");

export const api = {
	getProfile: () => client.call("get_profile"),
};
