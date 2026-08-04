"""Deterministic synthetic factory operations data."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd


DEFAULT_SEED = 42
DEFAULT_START_DATE = "2025-01-01"
PLANTS = ["Plant_A", "Plant_B", "Plant_C", "Plant_D"]
PRODUCT_FAMILIES = ["motor_control", "power_distribution", "automation"]
LINES = [f"Line_{index:02d}" for index in range(1, 7)]


def generate_daily_operations(
    n_days: int = 90,
    seed: int = DEFAULT_SEED,
    start_date: str = DEFAULT_START_DATE,
) -> pd.DataFrame:
    """Generate one row per plant, line, and day.

    A small synthetic deterioration pattern is injected into Plant_C / Line_02
    during the final two weeks so that the explainable alert logic has a
    reproducible case to surface.
    """

    if n_days < 35:
        raise ValueError("n_days must be at least 35 for a meaningful baseline")

    rng = np.random.default_rng(seed)
    dates = pd.date_range(start_date, periods=n_days, freq="D")
    rows = []

    for plant_index, plant_id in enumerate(PLANTS):
        plant_load_factor = 0.92 + plant_index * 0.045
        for line_index, line_id in enumerate(LINES):
            product_family = PRODUCT_FAMILIES[(plant_index + line_index) % len(PRODUCT_FAMILIES)]
            base_intensity = 1.45 + 0.17 * (line_index % 3) + 0.05 * plant_index
            base_load_kw = 72 + 8 * plant_index + 5 * (line_index % 2)
            for day_index, event_date in enumerate(dates):
                weekday_factor = 0.93 if event_date.weekday() >= 5 else 1.0
                production_units = int(
                    max(180, rng.poisson(1150 * plant_load_factor * weekday_factor))
                )
                downtime_min = float(max(2, rng.normal(34 + 4 * (line_index % 2), 12)))
                anomaly_injected = (
                    plant_id == "Plant_C" and line_id == "Line_02" and day_index >= n_days - 14
                )
                if anomaly_injected:
                    downtime_min += float(max(8, rng.normal(28, 6)))
                operating_hours = max(4.0, 16.0 - downtime_min / 60.0)
                energy_factor = 1.34 if anomaly_injected else 1.0
                energy_kwh = (
                    production_units * base_intensity * energy_factor
                    + base_load_kw * operating_hours
                    + rng.normal(0, 85)
                )
                energy_kwh = float(max(energy_kwh, production_units * 0.8))
                peak_kw = float(max(20, energy_kwh / operating_hours * rng.uniform(1.08, 1.34)))
                base_defect_rate = 0.006 + 0.002 * (line_index % 2)
                if anomaly_injected:
                    base_defect_rate += 0.006
                defect_units = int(rng.binomial(production_units, min(base_defect_rate, 0.08)))
                rows.append(
                    {
                        "event_date": event_date,
                        "plant_id": plant_id,
                        "line_id": line_id,
                        "product_family": product_family,
                        "production_units": production_units,
                        "operating_hours": round(operating_hours, 3),
                        "energy_kwh": round(energy_kwh, 2),
                        "peak_kw": round(peak_kw, 2),
                        "downtime_min": round(downtime_min, 2),
                        "defect_units": defect_units,
                        "ambient_temp_c": round(float(rng.normal(23, 4)), 2),
                    }
                )
    return pd.DataFrame(rows)


def generate_dataset(
    n_days: int = 90,
    seed: int = DEFAULT_SEED,
    start_date: str = DEFAULT_START_DATE,
) -> Dict[str, pd.DataFrame]:
    """Return the source tables used by the project."""

    return {
        "daily_operations": generate_daily_operations(
            n_days=n_days, seed=seed, start_date=start_date
        )
    }


def save_dataset(dataset: Dict[str, pd.DataFrame], output_dir: str | Path) -> None:
    """Write generated source tables to CSV."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for table_name, frame in dataset.items():
        frame.to_csv(output_path / f"{table_name}.csv", index=False, date_format="%Y-%m-%d")

