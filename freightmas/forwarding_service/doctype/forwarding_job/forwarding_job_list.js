// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
// List View Settings for Forwarding Job

frappe.listview_settings["Forwarding Job"] = {
  add_fields: ["date_created", "customer", "direction", "status"],

  // Optional: Define the field shown on the far right (optional)
  right_column: "status",

  // No status color indicators for now
  get_indicator: function(doc) {
    return [__(doc.status), "gray", "status,=," + doc.status];
  }
};
