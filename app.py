"""Streamlit dashboard for factory energy and operations KPIs."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from factory_energy_analytics.generate_data import generate_dataset  # noqa: E402
from factory_energy_analytics.pipeline import build_analysis  # noqa: E402


st.set_page_config(page_title="Factory Energy KPI Dashboard", page_icon="⚡", layout="wide")


@st.cache_data(show_spinner="正在生成运营数据并计算 KPI…")
def load_analysis() -> dict[str, pd.DataFrame]:
    weekly_path = PROJECT_ROOT / "artifacts" / "weekly_kpis.csv"
    summary_path = PROJECT_ROOT / "artifacts" / "plant_summary.csv"
    anomaly_path = PROJECT_ROOT / "artifacts" / "anomalies.csv"
    if weekly_path.exists() and summary_path.exists() and anomaly_path.exists():
        weekly = pd.read_csv(weekly_path, parse_dates=["week_start"])
        return {
            "weekly_kpis": weekly,
            "plant_summary": pd.read_csv(summary_path),
            "anomalies": pd.read_csv(anomaly_path, parse_dates=["week_start"]),
        }
    return build_analysis(generate_dataset(n_days=90, seed=42))


def percentage(value: float) -> str:
    return f"{value:.1%}"


analysis = load_analysis()
weekly = analysis["weekly_kpis"].copy()
summary = analysis["plant_summary"].copy()
anomalies = analysis["anomalies"].copy()
weekly["week_start"] = pd.to_datetime(weekly["week_start"])
anomalies["week_start"] = pd.to_datetime(anomalies["week_start"])

st.title("Factory Energy KPI Dashboard")
st.caption("Synthetic operations data · SQL KPI layer · Explainable anomaly rules")
st.info("数据为合成数据，仅用于工业运营分析方法演示，不代表真实工厂或设备结论。")

with st.sidebar:
    st.header("Filters")
    plants = st.multiselect("工厂", sorted(weekly["plant_id"].unique()), default=sorted(weekly["plant_id"].unique()))
    lines = st.multiselect("产线", sorted(weekly["line_id"].unique()), default=sorted(weekly["line_id"].unique()))
    levels = st.multiselect("告警级别", ["critical", "watch", "normal"], default=["critical", "watch", "normal"])

filtered = weekly[
    weekly["plant_id"].isin(plants)
    & weekly["line_id"].isin(lines)
    & weekly["alert_level"].isin(levels)
].copy()

cards = st.columns(5)
cards[0].metric("产线数", f"{filtered['line_key'].nunique():,}")
cards[1].metric("平均单位能耗", f"{filtered['energy_intensity_kwh_per_unit'].mean():.2f} kWh/unit")
cards[2].metric("平均停机率", percentage(filtered["downtime_rate"].mean()))
cards[3].metric("异常周数", f"{(filtered['alert_level'] != 'normal').sum():,}")
cards[4].metric("平均缺陷率", percentage(filtered["defect_rate"].mean()))

overview, trend, actions = st.tabs(["工厂对比", "产线趋势", "异常排查"])

with overview:
    left, right = st.columns(2)
    with left:
        plant_view = summary[summary["plant_id"].isin(plants)].copy()
        fig = px.bar(
            plant_view,
            x="plant_id",
            y="avg_energy_intensity",
            color="alert_weeks",
            title="Average energy intensity by plant",
            labels={"avg_energy_intensity": "kWh / unit", "alert_weeks": "alert weeks"},
            color_continuous_scale="Oranges",
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.scatter(
            plant_view,
            x="avg_downtime_rate",
            y="avg_energy_intensity",
            size="total_production_units",
            color="alert_weeks",
            hover_name="plant_id",
            title="Energy intensity vs downtime",
            labels={"avg_downtime_rate": "downtime rate", "avg_energy_intensity": "kWh / unit"},
            color_continuous_scale="Oranges",
        )
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("Plant summary")
    st.dataframe(
        plant_view.style.format(
            {
                "avg_energy_intensity": "{:.3f}",
                "avg_downtime_rate": "{:.1%}",
                "avg_defect_rate": "{:.1%}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

with trend:
    if filtered.empty:
        st.warning("当前筛选没有数据，请调整筛选器。")
    else:
        fig = px.line(
            filtered,
            x="week_start",
            y="energy_intensity_kwh_per_unit",
            color="line_key",
            markers=True,
            title="Weekly energy intensity by production line",
            labels={"energy_intensity_kwh_per_unit": "kWh / unit", "week_start": "week"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            filtered.sort_values("energy_intensity_zscore", ascending=False).head(25)[
                [
                    "week_start",
                    "line_key",
                    "energy_intensity_kwh_per_unit",
                    "energy_intensity_zscore",
                    "downtime_rate",
                    "defect_rate",
                    "alert_level",
                ]
            ].style.format(
                {
                    "energy_intensity_kwh_per_unit": "{:.3f}",
                    "energy_intensity_zscore": "{:.2f}",
                    "downtime_rate": "{:.1%}",
                    "defect_rate": "{:.1%}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

with actions:
    selected_anomalies = anomalies[
        anomalies["plant_id"].isin(plants)
        & anomalies["line_id"].isin(lines)
        & anomalies["alert_level"].isin(levels)
    ].copy()
    st.subheader("Prioritized anomaly list")
    st.dataframe(
        selected_anomalies[
            [
                "week_start",
                "line_key",
                "alert_level",
                "alert_reason",
                "energy_intensity_kwh_per_unit",
                "energy_intensity_zscore",
                "downtime_rate",
                "defect_rate",
            ]
        ].style.format(
            {
                "energy_intensity_kwh_per_unit": "{:.3f}",
                "energy_intensity_zscore": "{:.2f}",
                "downtime_rate": "{:.1%}",
                "defect_rate": "{:.1%}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(
        """
        **建议排查顺序**

        1. 先核对电表、产量和时间窗口，排除数据质量问题；
        2. 再对比维护记录、停机原因和设备运行参数；
        3. 若能耗与停机同时升高，优先安排设备/工艺排查；
        4. 下一周复测单位能耗，验证动作是否有效。
        """
    )

