# Automated BL & Container Tracking — Technical Design Specification

> **Purpose:** This document is a complete technical specification for the automated BL and container tracking integration in the Forwarding Job module of FreightMas. It is intended to be used as context in VS Code Copilot Chat to guide implementation from scratch.

---

## Table of Contents

1. [Overview](#1-overview)
2. [The Three API Functions](#2-the-three-api-functions)
3. [New Doctype: Forwarding API Tracking Event](#3-new-doctype-forwarding-api-tracking-event-child-table)
4. [Changes to the Forwarding Job Doctype](#4-changes-to-forwarding-job-doctype)
5. [Changes to the cargo_parcel_details Doctype](#5-changes-to-cargo_parcel_details-doctype)
6. [New Settings Doctype: Shipping Tracker Settings](#6-new-settings-doctype-shipping-tracker-settings-single-doctype)
7. [New Integration Module Structure](#7-new-integration-module-structure)
8. [Scheduler Hook Change](#8-scheduler-hook-change)
9. [How Manual and API Tracking Work Together](#9-how-manual-and-api-tracking-work-together)
10. [UI Behaviour Notes](#10-ui-behaviour-notes)
11. [Implementation Order](#11-implementation-order)

---

## 1. Overview

### Purpose

This feature adds automated, daily tracking of Bills of Lading (BL) and their associated containers in the **Forwarding Job** module. Instead of relying solely on manual tracking comments, the system will call external shipping APIs on a daily schedule and populate structured tracking data directly on each Forwarding Job.

### External API Providers

Two providers are supported, selectable via a settings doctype:

| Provider | Description |
|---|---|
| **Searates** | `https://tracking.searates.com/tracking` — industry-standard BL and container tracking API |
| **Jsoncargo** | Alternative provider; used as fallback or primary depending on configuration |

A fallback mechanism allows the system to try Provider A first, and if no data is returned, automatically try Provider B.

### Tracking Lifecycle

- The daily scheduler queries all **Forwarding Jobs** that meet these criteria:
  - `status` NOT IN (`"Completed"`, `"Cancelled"`)
  - `bl_number` is not blank
  - `docstatus < 2`
  - `api_tracking_enabled = 1`
- For each qualifying job, BL-level events and per-container status are fetched from the API and saved.
- **Tracking stops automatically** when a job's status is set to `"Completed"` — the `api_tracking_enabled` field is automatically unchecked at that point.

---

## 2. The Three API Functions

### Function 1: One-Off "Fetch Containers from BL" Button

This is a **manual, on-demand** action triggered by the user to populate the `cargo_parcel_details` table from the BL number.

#### Location

Cargo Tab → **Bill of Lading Details** section, placed immediately after the `bl_number` field.

#### Visibility Conditions

The button is only visible when **all** of the following are true:

- `bl_number` is filled (not empty)
- `cargo_parcel_details` child table is empty (no rows yet)
- Job status is **not** `"Completed"`

> If `cargo_parcel_details` already has rows, the button shows a warning: *"Cargo details already exist. This will add additional rows. Continue?"*

#### Flow

1. User enters the BL number and saves (or the field is already filled).
2. User clicks the **"Fetch Containers from BL"** button.
3. A loading spinner is shown while the system calls the API with the `bl_number`.
4. The API returns the containers found under that BL.
5. A **preview dialog** is shown listing the found containers:

   | Container No | Type | Vessel | POL | POD | ETA |
   |---|---|---|---|---|---|
   | TCKU1234567 | 40HC | MSC ANNA | Qingdao | Durban | 2026-04-15 |

6. On user confirmation, rows are appended to `cargo_parcel_details`.

#### Fields Populated in Each New `cargo_parcel_details` Row

| Field | Value |
|---|---|
| `cargo_type` | `"Containerised"` |
| `container_number` | From API (e.g. `TCKU1234567`) |
| `container_type` | From API (e.g. `40HC`, `20GP`) — matched to existing Container Type link |
| `to_be_returned` | `1` (default; user can change) |

#### Fields Also Filled on the Forwarding Job (if currently blank)

| Forwarding Job Field | Source |
|---|---|
| `vessel_flight_no` | Vessel name + voyage from API |
| `vessel_flight_date` | From API |
| `port_of_loading` | From API |
| `port_of_discharge` | From API |
| `eta` | From API |
| `etd` | From API |

> These Forwarding Job fields are only filled if they are **currently blank** — existing user-entered values are never overwritten.

---

### Function 2: Daily BL-Level Tracking → New Child Table `bl_tracking_events`

This function runs automatically every day via the Frappe scheduler.

#### Scheduler Query

Fetches all Forwarding Jobs where:

```python
filters={
    "status": ["not in", ["Completed", "Cancelled"]],
    "bl_number": ["!=", ""],
    "docstatus": ["<", 2],
    "api_tracking_enabled": 1,
}
```

#### Per-Job Processing

For each qualifying job:

1. Calls the configured provider with `bl_number`.
2. **All events** returned are appended to the `bl_tracking_events` child table.
3. **Deduplication:** An event is only appended if no existing row has the same `event_code` + `event_date` combination.

#### Automatic Field Updates

Specific event codes from the API trigger automatic updates to Forwarding Job date fields. The update rules are:

| API Event Code | Forwarding Job Field Updated | Update Rule |
|---|---|---|
| `VESSEL_DEPARTURE` / `ATD` | `atd` | Only if field is currently blank |
| `VESSEL_ARRIVAL` / `ATA` / `PORT_ARRIVAL` | `ata` | Only if field is currently blank |
| `DISCHARGED` / `DISCHARGE_COMPLETE` | `discharge_date` | Only if field is currently blank |
| `ETA_UPDATE` | `eta` | Updates if new ETA differs by **more than 1 day** from current value |
| `VESSEL_DEPARTURE` | `etd` | Only if field is currently blank |
| `VESSEL_DEPARTURE` | `vessel_flight_no` | Only if field is currently blank |

> **Important:** User-entered values for `ata`, `atd`, `discharge_date`, `etd`, and `vessel_flight_no` are **never overwritten**. The exception is `eta`, which updates if the API value differs by more than 1 day — indicating a significant schedule change.

---

### Function 3: Daily Container-Level Tracking → `cargo_parcel_details` rows

This runs in the **same daily scheduler pass** as Function 2.

#### Per-Container Processing

For each non-completed job, the dispatcher loops through all rows in `cargo_parcel_details` where:

- `cargo_type` = `"Containerised"`
- `container_number` is not blank

For each such row, the API is called with the `container_number`.

#### Fields Updated on Each `cargo_parcel_details` Row

| Field | Description |
|---|---|
| `api_container_status` | Latest status text from API (e.g. `"Gate In at Durban Port"`) |
| `api_status_date` | Datetime of that status from the API |
| `api_last_updated` | Datetime the system last checked (set to `now()`) |

> All three fields are **read-only** and are always overwritten with the latest data — they represent the most recent known status, not a history log.

---

## 3. New Doctype: `Forwarding API Tracking Event` (Child Table)

This is a new child doctype that stores one row per BL-level event fetched from the API.

### Doctype Properties

| Property | Value |
|---|---|
| `istable` | `1` |
| `cannot_add_rows` | `1` |
| `cannot_delete_rows` | `1` |

All fields are `read_only: 1`.

### Fields

| Fieldname | Fieldtype | Label | Notes |
|---|---|---|---|
| `event_date` | Datetime | Event Date | When the event happened — sourced from API |
| `event_code` | Data | Event Code | e.g. `VESSEL_DEPARTURE`, `PORT_ARRIVAL`, `DISCHARGED` |
| `event_description` | Small Text | Description | Human-readable description from the API |
| `vessel_name` | Data | Vessel | e.g. `MSC ANNA` |
| `port_name` | Data | Port | e.g. `Durban`, `Qingdao` |
| `provider` | Data | Provider | `Searates` or `Jsoncargo` |
| `fetched_on` | Datetime | Fetched On | When the system retrieved this — auto-set to `now()` |

---

## 4. Changes to `Forwarding Job` Doctype

### New Fields

| Fieldname | Fieldtype | Label | Section | Notes |
|---|---|---|---|---|
| `api_tracking_enabled` | Check | Enable Auto-Tracking | Tracking Tab — top | User toggles. Automatically unchecked when job status changes to `"Completed"` |
| `last_api_tracked_on` | Datetime | Last API Sync | Tracking Tab — top | Read Only. Set by the scheduler after each run |
| `api_tracking_status` | Data | API Status | Tracking Tab — top | Read Only. e.g. `"Active"`, `"No data returned"`, `"Error: timeout"` |
| `bl_tracking_events` | Table | API Tracking Events | Tracking Tab — new section above `forwarding_tracking` | Links to `Forwarding API Tracking Event`. Read Only |
| `fetch_containers_from_bl` | Button | Fetch Containers from BL | Cargo Tab — Bill of Lading Details section, after `bl_number` | Triggers the one-off container fetch (Function 1) |

### Tracking Tab — Field Order After Changes

```
tracking_tab
│
├── api_tracking_section  (Section Break — label: "API / External Tracking")
│   ├── api_tracking_enabled
│   ├── column_break_api1
│   ├── last_api_tracked_on
│   ├── column_break_api2
│   └── api_tracking_status
│
├── bl_tracking_events          ← NEW child table, read-only, label: "API Tracking Events (Auto-Updated)"
│
├── manual_tracking_section  (Section Break — label: "Manual Tracking")
│   └── forwarding_tracking     ← existing, unchanged
│
├── section_break_eooh          ← existing
├── current_comment             ← existing; now fed by BOTH manual and API sources
├── column_break_hrnc
├── last_updated_by
├── column_break_afpk
└── last_updated_on
│
├── section_break_umkg
├── status
└── ...
```

---

## 5. Changes to `cargo_parcel_details` Doctype

Three new read-only fields are added in a new **"API Status"** section at the bottom of each row, placed after the existing `extended_tracking_section`.

### New Fields

| Fieldname | Fieldtype | Label | Notes |
|---|---|---|---|
| `api_status_section` | Section Break | API Tracking Status | New section break |
| `api_container_status` | Data | API Status | Read Only. `in_list_view: 1`. e.g. `"Arrived Durban"` |
| `api_status_date` | Datetime | Status Date | Read Only. When this status occurred |
| `api_last_updated` | Datetime | Last API Sync | Read Only. When the system last checked |

> **`api_container_status`** has `in_list_view: 1` so it appears as a column in the cargo parcel details grid on the Forwarding Job form.

---

## 6. New Settings Doctype: `Shipping Tracker Settings` (Single Doctype)

A single doctype for storing global API configuration. Only one record exists (Single type).

### Location

`freightmas/forwarding_service/doctype/shipping_tracker_settings/`

### Fields

| Fieldname | Fieldtype | Label | Notes |
|---|---|---|---|
| `is_enabled` | Check | Enable Tracking | Global on/off switch for all automated tracking |
| `tracking_provider` | Select | Provider | Options: `Searates`, `Jsoncargo` |
| `api_key` | Password | API Key | API key / token for the selected provider |
| `fallback_provider` | Select | Fallback Provider | Optional second provider if the first returns no data |
| `fallback_api_key` | Password | Fallback API Key | API key for the fallback provider |
| `notify_on_arrival` | Check | Notify on Arrival | Send a Frappe notification when `ata` is auto-filled by the API |

---

## 7. New Integration Module Structure

### Directory Layout

```
freightmas/integrations/__init__.py
freightmas/integrations/tracking/__init__.py
freightmas/integrations/tracking/base.py          # Abstract TrackingProvider class
freightmas/integrations/tracking/searates.py      # Searates API implementation
freightmas/integrations/tracking/jsoncargo.py     # Jsoncargo API implementation
freightmas/integrations/tracking/dispatcher.py    # Orchestrator: loops jobs, calls providers, saves results
```

---

### `base.py` — Abstract Contract

```python
class TrackingProvider:
    def fetch_bl_events(self, bl_number: str) -> list[dict]:
        """
        Fetch all BL-level tracking events for a given BL number.

        Returns a list of dicts, each with keys:
            - event_date        (str ISO datetime)
            - event_code        (str, e.g. "VESSEL_DEPARTURE")
            - event_description (str, human-readable)
            - vessel_name       (str)
            - port_name         (str)
        """
        ...

    def fetch_containers_for_bl(self, bl_number: str) -> list[dict]:
        """
        Fetch the list of containers under a given BL number.

        Returns a list of dicts, each with keys:
            - container_number  (str, e.g. "TCKU1234567")
            - container_type    (str, e.g. "40HC", "20GP")
            - vessel_name       (str)
            - vessel_voyage     (str)
            - port_of_loading   (str)
            - port_of_discharge (str)
            - eta               (str ISO date)
            - etd               (str ISO date)
        """
        ...

    def fetch_container_status(self, container_number: str) -> dict:
        """
        Fetch the latest status for a specific container number.

        Returns a dict with keys:
            - status        (str, e.g. "Gate In at Durban Port")
            - status_date   (str ISO datetime)
            - vessel_name   (str)
            - port_name     (str)
        """
        ...
```

---

### `dispatcher.py` — Key Functions

```python
import frappe
from frappe.utils import now_datetime, date_diff


def run_all_active_jobs():
    """
    Called daily by the Frappe scheduler.
    Entry point for all automated BL and container tracking.
    """
    # 1. Load Shipping Tracker Settings — if not enabled, return immediately
    settings = frappe.get_single("Shipping Tracker Settings")
    if not settings.is_enabled:
        return

    # 2. Query all qualifying Forwarding Jobs
    jobs = frappe.get_all(
        "Forwarding Job",
        filters={
            "status": ["not in", ["Completed", "Cancelled"]],
            "bl_number": ["!=", ""],
            "docstatus": ["<", 2],
            "api_tracking_enabled": 1,
        },
        fields=["name", "bl_number"],
    )

    # 3. Process each job, wrapping in try/except so one failure doesn't block others
    for job in jobs:
        try:
            run_tracking_for_job(job.name)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"BL Tracking failed for Forwarding Job: {job.name}"
            )


def run_tracking_for_job(job_name: str):
    """
    Run a full tracking update for a single Forwarding Job.

    Steps:
        1. Load the Forwarding Job document.
        2. Instantiate the correct provider from Shipping Tracker Settings.
        3. BL-level: fetch events → append new rows to bl_tracking_events
           (deduplicate by event_code + event_date).
        4. Apply event-driven field updates (atd, ata, discharge_date, eta, etd,
           vessel_flight_no) according to the mapping table in the design doc.
        5. Container-level: for each cargo_parcel_details row where
           cargo_type == "Containerised" and container_number is set,
           fetch status → update api_container_status, api_status_date,
           api_last_updated.
        6. Update last_api_tracked_on = now() and api_tracking_status = "Active".
        7. Call sync_current_comment(job) to keep current_comment up to date.
        8. Save the job (flags.ignore_permissions = True).
    """
    ...


def fetch_containers_and_populate(job_name: str) -> dict:
    """
    Whitelisted. Called when the user clicks "Fetch Containers from BL".
    Returns container data for the preview dialog — does NOT save yet.

    Returns:
        {
            "containers": [
                {
                    "container_number": "TCKU1234567",
                    "container_type": "40HC",
                    "vessel_name": "MSC ANNA",
                    "vessel_voyage": "123W",
                    "port_of_loading": "Qingdao",
                    "port_of_discharge": "Durban",
                    "eta": "2026-04-15",
                    "etd": "2026-03-01",
                },
                ...
            ],
            "job_fields": {
                "vessel_flight_no": "MSC ANNA / 123W",
                "port_of_loading": "Qingdao",
                "port_of_discharge": "Durban",
                "eta": "2026-04-15",
                "etd": "2026-03-01",
            }
        }
    """
    ...


def confirm_and_populate_containers(job_name: str, containers: list) -> int:
    """
    Whitelisted. Called after the user confirms the preview dialog.

    Actions:
        1. Load the Forwarding Job.
        2. For each container in `containers`, append a new row to
           cargo_parcel_details with:
               cargo_type       = "Containerised"
               container_number = container["container_number"]
               container_type   = container["container_type"]  (matched to Container Type link)
               to_be_returned   = 1
        3. Fill vessel_flight_no, port_of_loading, port_of_discharge, eta, etd
           on the Forwarding Job only if currently blank.
        4. Save the job.
        5. Return the count of rows added.
    """
    ...


def sync_current_comment(job):
    """
    Sets current_comment to whichever is newer:
    the last manual forwarding_tracking entry, or the last API bl_tracking_events entry.

    Logic:
        - Get the most recent row from forwarding_tracking (by updated_on).
        - Get the most recent row from bl_tracking_events (by fetched_on).
        - Whichever is newer becomes the source of current_comment,
          last_updated_by, and last_updated_on.
        - If only one source has data, use that source.
        - Manual tracking entries are NEVER deleted by this function.
    """
    ...
```

---

### `searates.py` — Searates Provider

```python
import frappe
import requests
from freightmas.integrations.tracking.base import TrackingProvider


class SearatesProvider(TrackingProvider):
    BASE_URL = "https://tracking.searates.com/tracking"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_bl_events(self, bl_number: str) -> list[dict]:
        """Call Searates API and return normalised event list."""
        ...

    def fetch_containers_for_bl(self, bl_number: str) -> list[dict]:
        """Call Searates API and return normalised container list."""
        ...

    def fetch_container_status(self, container_number: str) -> dict:
        """Call Searates API and return normalised container status."""
        ...
```

---

### `jsoncargo.py` — Jsoncargo Provider

```python
import frappe
import requests
from freightmas.integrations.tracking.base import TrackingProvider


class JsoncargoProvider(TrackingProvider):
    BASE_URL = "https://api.jsoncargo.com/track"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_bl_events(self, bl_number: str) -> list[dict]:
        """Call Jsoncargo API and return normalised event list."""
        ...

    def fetch_containers_for_bl(self, bl_number: str) -> list[dict]:
        """Call Jsoncargo API and return normalised container list."""
        ...

    def fetch_container_status(self, container_number: str) -> dict:
        """Call Jsoncargo API and return normalised container status."""
        ...
```

---

## 8. Scheduler Hook Change

In `freightmas/hooks.py`, add the new daily scheduler entry alongside the existing one:

```python
scheduler_events = {
    "daily": [
        "freightmas.scheduler.quotation.expire_quotations",
        "freightmas.integrations.tracking.dispatcher.run_all_active_jobs",  # NEW
    ],
    # ... other events unchanged
}
```

---

## 9. How Manual and API Tracking Work Together

```
Manual forwarding_tracking  ──┐
                               ├──► current_comment = most recent of the two
API bl_tracking_events      ──┘    (recalculated on save + after each API sync)

API bl_tracking_events      ──────► Fills eta / ata / discharge_date / etd / atd
                                     (blank-only, except ETA: updates if > 1 day diff)

API container tracking      ──────► Updates api_container_status per container row
                                     (always overwrites — represents latest known status)

User "Fetch Containers"     ──────► Populates cargo_parcel_details rows
                                     (one-time on-demand, only if table is empty)
```

### Rules

| Rule | Detail |
|---|---|
| **Manual comments are preserved** | Manual `forwarding_tracking` rows are NEVER deleted or overwritten by the API. |
| **API field updates are non-destructive** | `ata`, `atd`, `discharge_date`, `etd`, `vessel_flight_no` are only filled when **blank**. |
| **ETA exception** | `eta` is updated if the API value differs from the current value by **more than 1 day**. |
| **Container status always overwrites** | `api_container_status`, `api_status_date`, `api_last_updated` are always updated — they are the latest known status, not history. |
| **Auto-disable on completion** | `api_tracking_enabled` is automatically set to `0` when the job status changes to `"Completed"`. |
| **API failures are silent** | If an API call fails, `api_tracking_status` is updated with the error message. All existing data on the job is unaffected. |

---

## 10. UI Behaviour Notes

### "Fetch Containers from BL" Button

- Shows a **loading spinner** (use `frappe.call` with `freeze: true`) while the API request is in flight.
- The confirmation dialog displays a formatted table:

  | Container No | Type | Vessel | POL | POD | ETA |
  |---|---|---|---|---|---|
  | TCKU1234567 | 40HC | MSC ANNA | Qingdao | Durban | 2026-04-15 |

- If `cargo_parcel_details` already has rows, display a warning before proceeding:
  > *"Cargo details already exist. This will add additional rows. Continue?"*

### `api_container_status` Column in Grid

- The `api_container_status` column in the `cargo_parcel_details` grid should be visually distinguished from manually-entered fields — use a **blue/teal highlight** via custom CSS or a `bold` label convention.

### Tracking Tab — API Events Table

- The `bl_tracking_events` child table label should read: **"API Tracking Events (Auto-Updated)"** to make clear to users that the table is read-only and system-managed.

### Error State

- When an API call fails, `api_tracking_status` should display a short, human-readable error, e.g.:
  - `"Error: Connection timeout"`
  - `"Error: Invalid BL number"`
  - `"No data returned"`

---

## 11. Implementation Order

Follow this order to avoid dependency issues:

1. **`Shipping Tracker Settings`** — Single doctype. API keys must be stored before any API calls can be made.
2. **`Forwarding API Tracking Event`** — Child doctype. Schema must exist before the dispatcher can write rows.
3. **New fields on `cargo_parcel_details`** — Add `api_container_status`, `api_status_date`, `api_last_updated`.
4. **New fields on `Forwarding Job`** — Add `api_tracking_enabled`, `last_api_tracked_on`, `api_tracking_status`, `bl_tracking_events` child table, and `fetch_containers_from_bl` button.
5. **Integration module** — Implement in this order: `base.py` → `searates.py` → `jsoncargo.py` → `dispatcher.py`.
6. **`forwarding_job.py`** — Add whitelisted functions: `fetch_containers_and_populate()`, `confirm_and_populate_containers()`, `sync_current_comment()`. Add auto-disable logic for `api_tracking_enabled` on job completion.
7. **`forwarding_job.js`** — Add "Fetch Containers from BL" button logic, confirmation dialog, and button visibility conditions.
8. **`hooks.py`** — Add the daily scheduler entry last, after everything else is tested.
9. **End-to-end test** — Test with real BL numbers using both providers. Verify deduplication, field update rules, and the preview dialog.

---

*End of specification.*
