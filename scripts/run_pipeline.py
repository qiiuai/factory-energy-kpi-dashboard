"""Generate data, build KPI tables, and write local artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from factory_energy_analytics.generate_data import DEFAULT_SEED, generate_dataset, save_dataset  # noqa: E402
from factory_energy_analytics.pipeline import build_analysis  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    dataset = generate_dataset(n_days=args.n_days, seed=args.seed)
    save_dataset(dataset, PROJECT_ROOT / "data" / "generated")
    analysis = build_analysis(dataset)

    artifact_dir = PROJECT_ROOT / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    analysis["weekly_kpis"].to_csv(artifact_dir / "weekly_kpis.csv", index=False)
    analysis["plant_summary"].to_csv(artifact_dir / "plant_summary.csv", index=False)
    analysis["anomalies"].to_csv(artifact_dir / "anomalies.csv", index=False)

    summary = {
        "daily_rows": len(dataset["daily_operations"]),
        "weekly_kpi_rows": len(analysis["weekly_kpis"]),
        "plants": int(analysis["plant_summary"]["plant_id"].nunique()),
        "lines": int(analysis["weekly_kpis"]["line_key"].nunique()),
        "alert_rows": len(analysis["anomalies"]),
        "critical_rows": int((analysis["weekly_kpis"]["alert_level"] == "critical").sum()),
        "seed": args.seed,
    }
    (artifact_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    print("Artifacts written to artifacts/")


if __name__ == "__main__":
    main()

