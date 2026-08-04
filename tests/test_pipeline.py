from __future__ import annotations

import pandas as pd

from factory_energy_analytics.generate_data import generate_dataset
from factory_energy_analytics.pipeline import build_analysis, run_sql_kpi_layer


def test_generation_is_reproducible() -> None:
    first = generate_dataset(n_days=45, seed=7)["daily_operations"]
    second = generate_dataset(n_days=45, seed=7)["daily_operations"]
    pd.testing.assert_frame_equal(first, second)


def test_sql_kpi_layer_has_expected_grain_and_valid_rates() -> None:
    dataset = generate_dataset(n_days=45, seed=11)
    kpis = run_sql_kpi_layer(dataset)
    assert kpis[["plant_id", "line_id", "week_start"]].drop_duplicates().shape[0] == len(kpis)
    assert (kpis["energy_intensity_kwh_per_unit"] > 0).all()
    assert kpis["downtime_rate"].between(0, 1).all()
    assert kpis["defect_rate"].between(0, 1).all()


def test_alert_logic_surfaces_injected_energy_event() -> None:
    analysis = build_analysis(generate_dataset(n_days=90, seed=42))
    weekly = analysis["weekly_kpis"]
    anomalies = analysis["anomalies"]
    assert len(anomalies) > 0
    assert ((anomalies["plant_id"] == "Plant_C") & (anomalies["line_id"] == "Line_02")).any()
    assert set(weekly["alert_level"].unique()).issubset({"normal", "watch", "critical"})

