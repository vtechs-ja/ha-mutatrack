"""Battery runtime forecasting for MutaTrack (v1.5).

Computes a "time remaining" estimate purely from telemetry MutaTrack is
already polling (SOC, instantaneous battery power, daily cumulative
charge/discharge energy) — no new API calls. Total battery capacity is not
present anywhere in the ValueClouds API response (SOC is percentage-only),
so this module treats capacity as either a user-configured value or one
derived empirically from observed charge/discharge cycles, and flags a
deviation warning if the two disagree. Only the "naive instantaneous rate"
and "rolling average discharge rate" tiers are implemented here; the
time-of-day pattern tier is tracked separately, not yet built.

See docs/architecture.md and the Confluence "Feature Roadmap & Open
Questions" v1.5 section for the full design writeup.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

_LOGGER = logging.getLogger(__name__)

# Field ids this module reads from coordinator data — see const.py and
# docs/api-reference.md for how these were identified in the live response.
SOC_FIELD_ID = "bt_battery_capacity"
DISCHARGE_POWER_FIELD_ID = "battery_active_discharging_power"
CHARGE_POWER_FIELD_ID = "eybond_read_4"
DISCHARGE_ENERGY_TODAY_FIELD_ID = "battery_energy_today_discharge"
CHARGE_ENERGY_TODAY_FIELD_ID = "battery_energy_today_charge"
# The inverter's own configured low-SOC cutoff (e.g. many setups switch to
# mains at 10% rather than fully discharging). Read live each poll rather
# than assumed, since it's a user-adjustable inverter setting that could
# change. "Time remaining" means time until this cutoff, not until 0% —
# otherwise the estimate overstates real runtime by however long it'd take
# to drain SOC the BMS will never actually use.
STOP_SOC_FIELD_ID = "eybond_ctrl_70_read"
DEFAULT_STOP_SOC_PERCENT = 0.0

ROLLING_WINDOW = timedelta(minutes=30)
# Below this net power, treat the battery as idle rather than charging or
# discharging — avoids phase-flapping on sensor noise around zero.
IDLE_DEADBAND_W = 20.0
# Ignore cycles with too small an SOC swing — noisy/unreliable for
# calibration (a 1-2% wobble isn't a real full cycle).
MIN_CYCLE_SOC_DELTA_PERCENT = 5.0
CAPACITY_DEVIATION_WARN_RATIO = 0.20
EMPIRICAL_CAPACITY_EMA_ALPHA = 0.3

Phase = Literal["charging", "discharging", "idle"]
CapacitySource = Literal["configured", "empirical", "unavailable"]
Confidence = Literal["none", "low", "medium", "high"]


@dataclass
class _Sample:
    timestamp: datetime
    soc_percent: float
    stop_soc_percent: float
    net_power_w: float  # positive = discharging, negative = charging
    discharge_energy_today_kwh: float
    charge_energy_today_kwh: float

    @property
    def phase(self) -> Phase:
        if self.net_power_w > IDLE_DEADBAND_W:
            return "discharging"
        if self.net_power_w < -IDLE_DEADBAND_W:
            return "charging"
        return "idle"


@dataclass
class ForecastResult:
    """What sensor.py exposes as the forecast entity's state/attributes."""

    seconds_remaining: float | None
    rate_method: str
    capacity_source: CapacitySource
    capacity_kwh: float | None
    calibration_confidence: Confidence
    deviation_warning: bool
    observed_cycles: int
    stop_soc_percent: float


class BatteryForecastEngine:
    """Stateful engine, one instance per config entry, fed on every poll.

    In-memory only for this first cut — calibration state (empirical
    capacity, observed cycle count) resets on integration reload/HA
    restart. Acceptable for v1.5's initial scope; revisit if the
    reconvergence time after a restart proves annoying in practice.
    """

    def __init__(self, configured_capacity_kwh: float | None) -> None:
        self._configured_capacity_kwh = configured_capacity_kwh
        self._samples: deque[_Sample] = deque()
        self._empirical_capacity_kwh: float | None = None
        self._observed_cycles = 0
        self._cycle_start: _Sample | None = None

    def set_configured_capacity(self, capacity_kwh: float | None) -> None:
        """Update the user-configured capacity (options flow changed)."""
        self._configured_capacity_kwh = capacity_kwh

    def update(self, fields: dict[str, dict]) -> ForecastResult:
        sample = _sample_from_fields(fields)
        if sample is None:
            return ForecastResult(
                seconds_remaining=None,
                rate_method="unavailable",
                capacity_source="unavailable",
                capacity_kwh=None,
                calibration_confidence="none",
                deviation_warning=False,
                observed_cycles=self._observed_cycles,
                stop_soc_percent=DEFAULT_STOP_SOC_PERCENT,
            )

        self._detect_cycle_and_calibrate(sample)
        self._samples.append(sample)
        self._evict_old_samples(sample.timestamp)

        capacity_kwh, capacity_source = self._resolve_capacity()
        deviation_warning = self._has_capacity_deviation()
        confidence = self._calibration_confidence(capacity_source)

        avg_discharge_w = self._rolling_average_discharge_power_w()
        rate_method = "rolling_average" if len(self._samples) > 1 else "instantaneous"

        seconds_remaining: float | None = None
        if capacity_kwh is not None and avg_discharge_w and avg_discharge_w > 0:
            usable_soc_percent = max(0.0, sample.soc_percent - sample.stop_soc_percent)
            remaining_kwh = capacity_kwh * (usable_soc_percent / 100)
            seconds_remaining = remaining_kwh / (avg_discharge_w / 1000) * 3600

        return ForecastResult(
            seconds_remaining=seconds_remaining,
            rate_method=rate_method,
            capacity_source=capacity_source,
            capacity_kwh=capacity_kwh,
            calibration_confidence=confidence,
            deviation_warning=deviation_warning,
            observed_cycles=self._observed_cycles,
            stop_soc_percent=sample.stop_soc_percent,
        )

    def _resolve_capacity(self) -> tuple[float | None, CapacitySource]:
        if self._configured_capacity_kwh is not None:
            return self._configured_capacity_kwh, "configured"
        if self._empirical_capacity_kwh is not None:
            return self._empirical_capacity_kwh, "empirical"
        return None, "unavailable"

    def _has_capacity_deviation(self) -> bool:
        if self._configured_capacity_kwh is None or self._empirical_capacity_kwh is None:
            return False
        diff_ratio = abs(self._configured_capacity_kwh - self._empirical_capacity_kwh) / (
            self._configured_capacity_kwh
        )
        return diff_ratio > CAPACITY_DEVIATION_WARN_RATIO

    def _calibration_confidence(self, capacity_source: CapacitySource) -> Confidence:
        if capacity_source == "unavailable":
            return "none"
        if capacity_source == "configured" and self._empirical_capacity_kwh is None:
            return "low"
        if self._observed_cycles >= 5:
            return "high"
        if self._observed_cycles >= 2:
            return "medium"
        return "low"

    def _rolling_average_discharge_power_w(self) -> float | None:
        discharging = [s for s in self._samples if s.phase == "discharging"]
        if not discharging:
            return None
        return sum(s.net_power_w for s in discharging) / len(discharging)

    def _evict_old_samples(self, now: datetime) -> None:
        cutoff = now - ROLLING_WINDOW
        while self._samples and self._samples[0].timestamp < cutoff:
            self._samples.popleft()

    def _detect_cycle_and_calibrate(self, sample: _Sample) -> None:
        """Fold a completed charge/discharge cycle into the empirical EMA.

        A cycle is bounded by phase transitions into/out of "discharging"
        or "charging". Energy deltas come from the daily cumulative
        counters, which reset at midnight — a cycle spanning the reset is
        skipped (negative delta) rather than corrupting the estimate.
        """
        last = self._samples[-1] if self._samples else None
        last_phase = last.phase if last else "idle"

        if last_phase != "discharging" and sample.phase == "discharging":
            self._cycle_start = sample
        elif last_phase != "charging" and sample.phase == "charging":
            self._cycle_start = sample
        elif last_phase in ("discharging", "charging") and sample.phase != last_phase:
            self._finish_cycle(last_phase, sample)
            self._cycle_start = None

    def _finish_cycle(self, phase: Phase, end_sample: _Sample) -> None:
        start = self._cycle_start
        if start is None:
            return

        if phase == "discharging":
            soc_delta = start.soc_percent - end_sample.soc_percent
            energy_delta = (
                end_sample.discharge_energy_today_kwh - start.discharge_energy_today_kwh
            )
        else:
            soc_delta = end_sample.soc_percent - start.soc_percent
            energy_delta = end_sample.charge_energy_today_kwh - start.charge_energy_today_kwh

        if soc_delta < MIN_CYCLE_SOC_DELTA_PERCENT or energy_delta <= 0:
            # Too small to trust, or a day-boundary counter reset.
            return

        observed_capacity_kwh = energy_delta / (soc_delta / 100)

        if self._empirical_capacity_kwh is None:
            self._empirical_capacity_kwh = observed_capacity_kwh
        else:
            self._empirical_capacity_kwh = (
                EMPIRICAL_CAPACITY_EMA_ALPHA * observed_capacity_kwh
                + (1 - EMPIRICAL_CAPACITY_EMA_ALPHA) * self._empirical_capacity_kwh
            )
        self._observed_cycles += 1
        _LOGGER.debug(
            "MutaTrack forecast: observed %s cycle, capacity=%.2fkWh, empirical EMA=%.2fkWh (n=%d)",
            phase,
            observed_capacity_kwh,
            self._empirical_capacity_kwh,
            self._observed_cycles,
        )


def _sample_from_fields(fields: dict[str, dict]) -> _Sample | None:
    def _value(field_id: str) -> float | None:
        field = fields.get(field_id)
        if field is None:
            return None
        value = field.get("value")
        return value if isinstance(value, (int, float)) else None

    soc = _value(SOC_FIELD_ID)
    discharge_w = _value(DISCHARGE_POWER_FIELD_ID)
    charge_w = _value(CHARGE_POWER_FIELD_ID)
    discharge_kwh_today = _value(DISCHARGE_ENERGY_TODAY_FIELD_ID)
    charge_kwh_today = _value(CHARGE_ENERGY_TODAY_FIELD_ID)
    # Read live, not cached — this is a user-adjustable inverter setting.
    # Missing/non-numeric (e.g. unsupported firmware) falls back to 0, i.e.
    # "assume it can discharge to empty" — the pre-fix behavior.
    stop_soc = _value(STOP_SOC_FIELD_ID)
    if stop_soc is None:
        stop_soc = DEFAULT_STOP_SOC_PERCENT

    if soc is None or discharge_w is None or charge_w is None:
        return None
    if discharge_kwh_today is None or charge_kwh_today is None:
        return None

    return _Sample(
        timestamp=datetime.now(),
        soc_percent=soc,
        stop_soc_percent=stop_soc,
        net_power_w=discharge_w - charge_w,
        discharge_energy_today_kwh=discharge_kwh_today,
        charge_energy_today_kwh=charge_kwh_today,
    )
