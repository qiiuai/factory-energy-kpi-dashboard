"""DuckDB KPI aggregation and explainable anomaly rules."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import duckdb
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_KPI_PATH = PROJECT_ROOT / "sql" / "energy_kpi.sql"


def run_sql_kpi_layer(dataset: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Execute the weekly KPI SQL query against registered pandas tables."""

    connection = duckdb.connect(database=":memory:")
    try:
        for table_name, frame in dataset.items():
            connection.register(table_name, frame)
        query = SQL_KPI_PATH.read_text(encoding="utf-8")
        return connection.execute(query).df()
    finally:
        connection.close()


def add_alerts(weekly_kpis: pd.DataFrame) -> pd.DataFrame:
    """Add line-baseline z-scores and simple operational alert levels."""

    kpis = weekly_kpis.copy()
    kpis["line_key"] = kpis["plant_id"] + " / " + kpis["line_id"]
    group = kpis.groupby("line_key")["energy_intensity_kwh_per_unit"]
    line_mean = group.transform("mean")
    line_std = group.transform("std").replace(0, np.nan).fillna(0.0001)
    kpis["energy_intensity_zscore"] = (
        (kpis["energy_intensity_kwh_per_unit"] - line_mean) / line_std
    ).round(3)
    kpis["alert_level"] = np.select(
        [
            (kpis["energy_intensity_zscore"] >= 2.0) | (kpis["downtime_rate"] >= 0.12),
            (kpis["energy_intensity_zscore"] >= 1.25) | (kpis["downtime_rate"] >= 0.08),
        ],
        ["critical", "watch"],
        default="normal",
    )
    kpis["alert_reason"] = np.select(
        [
            (kpis["energy_intensity_zscore"] >= 2.0) & (kpis["downtime_rate"] >= 0.12),
            kpis["energy_intensity_zscore"] >= 2.0,
            kpis["downtime_rate"] >= 0.12,
            kpis["energy_intensity_zscore"] >= 1.25,
            kpis["downtime_rate"] >= 0.08,
        ],
        [
            "high energy intensity + high downtime",
            "energy intensity above line baseline",
            "downtime rate above threshold",
            "energy intensity worth watching",
            "downtime rate worth watching",
        ],
        default="within baseline",
    )
    return kpis.sort_values(["week_start", "plant_id", "line_id"]).reset_index(drop=True)


def build_analysis(dataset: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Build KPI, plant summary, and anomaly tables."""

    weekly_kpis = add_alerts(run_sql_kpi_layer(dataset))
    plant_summary = (
        weekly_kpis.groupby("plant_id", as_index=False)
        .agg(
            total_production_units=("production_units", "sum"),
            total_energy_kwh=("energy_kwh", "sum"),
            avg_energy_intensity=("energy_intensity_kwh_per_unit", "mean"),
            avg_downtime_rate=("downtime_rate", "mean"),
            avg_defect_rate=("defect_rate", "mean"),
            alert_weeks=("alert_level", lambda values: int((values != "normal").sum())),
        )
        .sort_values("avg_energy_intensity", ascending=False)
        .reset_index(drop=True)
    )
    plant_summary["energy_rank"] = np.arange(1, len(plant_summary) + 1)
    anomalies = weekly_kpis[weekly_kpis["alert_level"] != "normal"].copy()
    anomalies = anomalies.sort_values(
        ["alert_level", "energy_intensity_zscore"], ascending=[True, False]
    ).reset_index(drop=True)
    return {
        "weekly_kpis": weekly_kpis,
        "plant_summary": plant_summary,
        "anomalies": anomalies,
    }

