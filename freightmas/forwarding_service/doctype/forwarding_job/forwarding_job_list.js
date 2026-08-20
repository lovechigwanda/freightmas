// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
// List View Settings for Forwarding Job

const PHASE_LABELS = {
	planning: "Planning",
	awaiting_departure: "Awaiting Departure",
	in_transit: "In Transit",
	at_terminal: "At Terminal",
	under_port_clearance: "Under Port Clearance",
	under_border_clearance: "Under Border Clearance",
	on_road: "On Road",
	at_warehouse: "At Warehouse",
	delivered: "Delivered",
	closed: "Closed",
	cancelled: "Cancelled",
};

const PHASE_INDICATORS = {
	planning: "gray",
	awaiting_departure: "gray",
	in_transit: "blue",
	at_terminal: "orange",
	under_port_clearance: "purple",
	under_border_clearance: "purple",
	on_road: "yellow",
	at_warehouse: "orange",
	delivered: "green",
	closed: "darkgrey",
	cancelled: "red",
};

frappe.listview_settings["Forwarding Job"] = {
  add_fields: ["date_created", "customer", "direction", "status", "operational_phase", "operational_substage"],

  right_column: "operational_phase",

  get_indicator: function(doc) {
    if (doc.operational_phase) {
      const phaseLabel = PHASE_LABELS[doc.operational_phase] || doc.operational_phase;
      const label = doc.operational_substage
        ? `${phaseLabel} · ${doc.operational_substage}`
        : phaseLabel;
      const color = PHASE_INDICATORS[doc.operational_phase] || "gray";
      return [label, color, "operational_phase,=," + doc.operational_phase];
    }
    return [__(doc.status), "gray", "status,=," + doc.status];
  }
};
