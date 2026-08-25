export async function logout(redirectTo = "/login?redirect-to=/supplier-portal") {
	await fetch("/api/method/freightmas.portal.supplier.profile.logout", {
		method: "POST",
		credentials: "same-origin",
		headers: {
			"X-Frappe-CSRF-Token": window.csrf_token || "",
			Accept: "application/json",
		},
	});
	window.location.href = redirectTo;
}
