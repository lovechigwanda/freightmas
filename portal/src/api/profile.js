import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.api.profile");

export const api = {
	getProfile: () => client.call("get_profile"),
};
