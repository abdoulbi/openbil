"""Run reproducible latest-vintage backtests on all eligible current series."""

import argparse
import json
import pandas as pd
from sqlalchemy import text
from openbil.db import engine
from openbil.forecast import forecast


def evaluate(url):
    e = engine(url)
    with e.connect() as c:
        df = pd.read_sql(text("SELECT * FROM current_observations"), c)
    e.dispose()
    results = []
    for (country, indicator), g in df.groupby(["country_id", "indicator_id"]):
        row = {"country_id": country, "indicator_id": indicator}
        try:
            f = forecast(g)
            row.update(
                status="evaluated",
                model=f["model"],
                test_mae=f["test_mae"],
                test_rmse=f["test_rmse"],
                naive_test_mae=f["naive_test_mae"],
                validation_mae=f["validation_mae"],
                training_start=f["training_start"],
                training_end=f["training_end"],
                versions=g.version_id.unique().tolist(),
                test=f["test"].to_dict(orient="records"),
            )
        except ValueError as exc:
            row.update(status="ineligible", reason=str(exc))
        results.append(row)
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", required=True)
    p.add_argument("--output", default="docs/forecast-evaluation.json")
    a = p.parse_args()
    results = evaluate(a.database_url)
    with open(a.output, "w") as f:
        json.dump(results, f, indent=2)
    print(
        json.dumps(
            {
                "series": len(results),
                "evaluated": sum(r["status"] == "evaluated" for r in results),
                "ineligible": sum(r["status"] == "ineligible" for r in results),
            }
        )
    )
