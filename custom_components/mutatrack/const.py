"""Constants for the MutaTrack integration.

Data source confirmed live 2026-07-10 against Deron's real account (see
docs/api-reference.md for full findings). v1 uses `queryDeviceOneDataxxx`,
a self-describing named-field endpoint, NOT the originally-documented
`deviceDats` positional array — that array required guessing field
indices with no way to verify them; this endpoint returns id/title/unit/val
for every field, eliminating that whole class of risk.

`queryDeviceOneDataxxx` (115 fields) is a confirmed strict superset of the
leaner `querySPDeviceLastData` (48 fields) — same telemetry ids, plus
current control/settings values (OutPriority, charge current limits, etc.).
Rather than call both endpoints, PRIMARY_TELEMETRY_IDS below (the 48 lean
ids) is used to decide which fields become regular sensors vs. read-only
diagnostic-category sensors from the single richer response.
"""

from __future__ import annotations

DOMAIN = "mutatrack"

BASE_URL = "https://api.valueclouds.com"
LOGIN_ENDPOINT = f"{BASE_URL}/ppr/web/login/login"
DEVICE_ONE_DATA_ENDPOINT = f"{BASE_URL}/ppe/api/auth/web/queryDeviceOneDataxxx"

CONF_PN = "pn"
CONF_SN = "sn"
CONF_DEVCODE = "devcode"
CONF_DEVADDR = "devaddr"

# Confirmed live 2026-07-10 via browser DevTools capture — the originally
# documented default of 1 was an unverified guess and was wrong for this
# account.
DEFAULT_DEVADDR = 255
DEFAULT_I18N = "en_US"

# Underlying device reports to the cloud roughly every 5 minutes; polling
# faster has limited observed value (see docs/api-reference.md).
DEFAULT_SCAN_INTERVAL_SECONDS = 300
MIN_SCAN_INTERVAL_SECONDS = 120

HEADER_PROJECT = "IOT"

# The 48 field ids returned by querySPDeviceLastData — confirmed live
# 2026-07-10 to be a strict subset of queryDeviceOneDataxxx's 115 ids.
# Membership here marks a field as core v1 monitoring; everything else in
# the queryDeviceOneDataxxx response (settings/control-read values, machine
# info, etc.) is still exposed, but as a diagnostic-category sensor.
PRIMARY_TELEMETRY_IDS: frozenset[str] = frozenset(
    {
        "battery_active_discharging_power",
        "battery_energy_today_charge",
        "battery_energy_today_discharge",
        "bc_eybond_read_100",
        "bc_eybond_read_101",
        "bc_eybond_read_102",
        "bc_eybond_read_103",
        "bc_eybond_read_104",
        "bc_eybond_read_13",
        "bc_eybond_read_14",
        "bc_eybond_read_15",
        "bc_eybond_read_16",
        "bc_eybond_read_17",
        "bc_eybond_read_18",
        "bt_battery_capacity",
        "bt_battery_current",
        "bt_eybond_read_1",
        "bt_eybond_read_30",
        "energy_today",
        "energy_today_to_grid",
        "energy_total",
        "energy_total_to_grid",
        "gd_eybond_read_110",
        "gd_eybond_read_112",
        "gd_eybond_read_113",
        "gd_eybond_read_116",
        "gd_eybond_read_117",
        "gd_eybond_read_127",
        "gd_eybond_read_128",
        "gd_eybond_read_20",
        "gd_eybond_read_21",
        "gd_eybond_read_23",
        "gd_gridr_current",
        "load_active_power",
        "load_energy_today",
        "load_energy_total",
        "pv_eybond_read_10",
        "pv_eybond_read_12",
        "pv_eybond_read_7",
        "pv_eybond_read_9",
        "pv_output_power",
        "pv_voltage_1",
        "pv_voltage_2",
        "sy_eybond_read_31",
        "sy_eybond_read_86",
        "sy_eybond_read_88",
        "sy_eybond_read_89",
        "sy_invvolt",
    }
)

# Cumulative energy field ids that must get device_class ENERGY +
# state_class TOTAL_INCREASING for Home Assistant Energy Dashboard
# compatibility. Confirmed live via each field's "kWh" unit and
# monotonically-accumulating name (e.g. "...Today", "...Total").
ENERGY_FIELD_IDS: frozenset[str] = frozenset(
    {
        "energy_today",
        "energy_total",
        "energy_today_to_grid",
        "energy_total_to_grid",
        "battery_energy_today_charge",
        "battery_energy_today_discharge",
        "load_energy_today",
        "load_energy_total",
    }
)

# The one field id known to represent battery state of charge — gets
# device_class BATTERY instead of the generic "%" handling.
BATTERY_SOC_FIELD_ID = "bt_battery_capacity"
