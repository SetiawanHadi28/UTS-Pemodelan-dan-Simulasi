from __future__ import annotations

import numpy as np
from flask import Flask, render_template, request

from inventory_model import (
    InventoryParams,
    simulate_inventory,
    summarize,
    scenario_curves,
)

app = Flask(__name__)

DEFAULT_PARAMS = InventoryParams()


def sample_rows(df, n: int = 20):
    idx = np.linspace(0, len(df) - 1, num=min(n, len(df)), dtype=int)
    return df.iloc[idx].reset_index(drop=True).round(2).to_dict("records")


@app.route("/", methods=["GET", "POST"])
def index():
    params = DEFAULT_PARAMS
    df = None
    summary = None
    sample = []
    chart_data = []
    scenario_chart = None

    if request.method == "POST":
        params = InventoryParams(
            days=int(request.form.get("days", params.days)),
            initial_stock=int(request.form.get("initial_stock", params.initial_stock)),
            reorder_point=int(request.form.get("reorder_point", params.reorder_point)),
            reorder_qty=int(request.form.get("reorder_qty", params.reorder_qty)),
            mean_demand=float(request.form.get("mean_demand", params.mean_demand)),
            demand_std=float(request.form.get("demand_std", params.demand_std)),
            lead_time=int(request.form.get("lead_time", params.lead_time)),
            seed=int(request.form.get("seed", params.seed)),
        )

        df = simulate_inventory(**params.__dict__)
        summary = summarize(df)
        sample = sample_rows(df)
        chart_data = df[["Hari", "Stok tersedia", "Backlog"]].round(2).to_dict("records")
        scenario_df = scenario_curves(params.days)
        scenario_chart = {
            "labels": scenario_df["Hari"].tolist(),
            "datasets": [
                {"label": col, "data": scenario_df[col].tolist()}
                for col in scenario_df.columns
                if col != "Hari"
            ],
        }

    return render_template(
        "inventory.html",
        params=params,
        summary=summary,
        sample=sample,
        chart_data=chart_data,
        scenario_chart=scenario_chart,
        submitted=df is not None,
    )


if __name__ == "__main__":
    app.run(debug=True)

