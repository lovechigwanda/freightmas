// Shared fetch helper for the Client Portal. Runs same-origin inside a
// logged-in Frappe (Website User) session, so the browser already carries
// the session cookie - we only need to attach the CSRF token the www/
// page's Jinja template injects as window.csrf_token.
//
// Each api/*.js module creates its own client bound to its whitelisted
// Python module path via createApiClient(prefix).

function buildUrl(prefix, method, params = {}) {
	const url = `/api/method/${prefix}.${method}`;
	const query = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value === undefined || value === null || value === "") return;
		query.append(key, typeof value === "object" ? JSON.stringify(value) : value);
	});
	return query.toString() ? `${url}?${query.toString()}` : url;
}

// Frappe reports errors via a `_server_messages` field that is itself a
// JSON-encoded array of JSON-encoded {message, title, indicator} objects -
// double-encoded, not a plain string. Unwrap it so the UI can show a clean
// sentence instead of the raw nested-JSON payload.
function extractServerMessage(payload) {
	const raw = payload && payload._server_messages;
	if (!raw) return "";
	try {
		const messages = JSON.parse(raw);
		return messages
			.map((m) => {
				try {
					return JSON.parse(m).message;
				} catch (e) {
					return m;
				}
			})
			.filter(Boolean)
			.join(" ");
	} catch (e) {
		return "";
	}
}

async function call(prefix, method, params = {}) {
	const fullUrl = buildUrl(prefix, method, params);

	const res = await fetch(fullUrl, {
		method: "GET",
		credentials: "same-origin",
		headers: {
			"X-Frappe-CSRF-Token": window.csrf_token || "",
			Accept: "application/json",
		},
	});

	if (!res.ok) {
		let detail = "";
		try {
			detail = extractServerMessage(await res.json());
		} catch (e) {
			// ignore - not JSON
		}
		throw new Error(detail || `Request to ${method} failed (${res.status}).`);
	}

	const data = await res.json();
	return data.message;
}

export function createApiClient(prefix) {
	return {
		call: (method, params) => call(prefix, method, params),
		buildUrl: (method, params) => buildUrl(prefix, method, params),
	};
}
