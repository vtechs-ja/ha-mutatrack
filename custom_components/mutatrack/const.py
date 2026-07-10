"""Constants for the MutaTrack integration.

Field index map is UNVERIFIED — reverse-engineered from a community gist
built for a different Must PV18-3224 PRO unit. See ../../docs/api-reference.md
for status and the "Live validation findings" section, which Phase 2
(local API test harness) is responsible for filling in before this map is
trusted for a public release.
"""

from __future__ import annotations

DOMAIN = "mutatrack"

BASE_URL = "https://api.valueclouds.com"
LOGIN_ENDPOINT = f"{BASE_URL}/ppr/web/login/login"
DEVICE_DATS_ENDPOINT = f"{BASE_URL}/drt/api/auth/web/deviceDats"

CONF_PN = "pn"
CONF_SN = "sn"
CONF_DEVCODE = "devcode"
CONF_DEVADDR = "devaddr"

DEFAULT_DEVADDR = 1
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 1

# Underlying device reports to the cloud roughly every 5 minutes; polling
# faster has limited observed value (see docs/api-reference.md).
DEFAULT_SCAN_INTERVAL_SECONDS = 300
MIN_SCAN_INTERVAL_SECONDS = 120

HEADER_PROJECT = "IOT"
HEADER_I18N = "ru_RU"

# Field map is 1-indexed to match the Confluence/community-gist
# documentation convention. Use `FIELD_INDEX[key] - 1` for zero-indexed
# Python list access into the raw `data.row[0].field` array.
FIELD_INDEX: dict[str, int] = {
    "last_update_timestamp": 1,
    "battery_voltage": 2,
    "pv1_voltage": 3,
    "pv2_voltage": 4,
    "inverter_voltage": 5,
    "bms_battery_voltage": 6,
    "load_current": 7,
    "battery_current": 8,
    "pv1_charger_current": 9,
    "bms_battery_current": 10,
    "pv2_charger_current": 11,
    "pv1_charger_power": 12,
    "pv2_charger_power": 13,
    "pv_total_power": 14,
    "battery_soc": 15,
    "load_power": 16,
    "grid_power": 17,
    "work_state": 18,
    "grid_voltage": 19,
    "software_version": 20,
    "rated_power": 21,
    "inverter_current": 22,
    "grid_current": 23,
    "inverter_active_power": 24,
    "inverter_apparent_power": 25,
    "grid_apparent_power": 26,
    "load_apparent_power": 27,
    "inverter_reactive_power": 28,
    "grid_reactive_power": 29,
    "load_reactive_power": 30,
    "inverter_frequency": 31,
    "grid_frequency": 32,
    "ac_radiator_temperature": 33,
    "transformer_temperature": 34,
    "dc_radiator_temperature": 35,
    "accumulated_charge_energy": 36,
    "accumulated_discharge_energy": 37,
    "accumulated_buy_energy": 38,
    "accumulated_sell_energy": 39,
    "accumulated_load_energy": 40,
    "accumulated_self_use_energy": 41,
    "battery_power": 42,
    "charger_work_enable": 43,
    "pv_cumulative_generation": 44,
    "bms_battery_temperature": 45,
}
