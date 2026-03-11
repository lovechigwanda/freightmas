/* FreightMas Session Expiry Handler
 * Intercepts session-expired AJAX errors and shows a user-friendly
 * "Session Expired" dialog instead of the default "Method Not Allowed" error.
 */

(function () {
	let sessionExpiredDialogShown = false;

	$(document).ajaxError(function (event, xhr) {
		if (sessionExpiredDialogShown) return;

		// Only intercept 403 (Forbidden) or 401 (Unauthorized) responses
		if (xhr.status === 403 || xhr.status === 401) {
			let responseText = "";
			try {
				responseText = xhr.responseText || "";
			} catch (e) {
				return;
			}

			// Detect session expiry: Frappe returns "Login to access" in the
			// response body when a guest (expired session) calls a protected
			// method.  This string is set in frappe.handler and is the most
			// reliable indicator that distinguishes session expiry from a
			// normal permission error.
			if (responseText.includes("Login to access")) {
				sessionExpiredDialogShown = true;

				// Short delay so any Frappe error dialog that was already
				// queued by the default handler renders first – we then
				// close it and replace it with our own friendly message.
				setTimeout(function () {
					// Close existing Frappe error dialogs
					if (frappe.msg_dialog && frappe.msg_dialog.$wrapper) {
						frappe.msg_dialog.hide();
					}

					// Show user-friendly session expired dialog
					let d = new frappe.ui.Dialog({
						title: __("Session Expired"),
						primary_action_label: __("Log In"),
						primary_action: function () {
							window.location.href = "/login";
						},
					});

					d.$body.html(
						'<div style="text-align:center; padding: 15px 0;">' +
							'<div style="font-size: 48px; margin-bottom: 15px;">&#x1F512;</div>' +
							"<p>" +
							__("Your session has expired due to inactivity.") +
							"<br>" +
							__("Please log in again to continue.") +
							"</p>" +
							"</div>"
					);

					// Redirect to login on any form of dismissal
					d.on_hide = function () {
						window.location.href = "/login";
					};

					d.show();
				}, 200);
			}
		}
	});
})();
