from __future__ import annotations

import numpy as np
from flask import Flask, render_template, request

from dataclasses import dataclass
import pandas as pd


@dataclass
class InventoryParams:
    days: int = 180
    initial_stock: int = 800
    reorder_point: int = 300
    reorder_qty: int = 600
    mean_demand: float = 120.0
    demand_std: float = 30.0
    lead_time: int = 7
    seed: int = 42


def simulate_inventory(params: InventoryParams) -> pd.DataFrame:
    rng = np.random.default_rng(params.seed)
    stock = params.initial_stock
    backlog = 0.0
    pipeline: list[dict[str, int]] = []
    records = []

    for day in range(params.days + 1):
        deliveries = sum(o["qty"] for o in pipeline if o["arrival"] == day)
        pipeline = [o for o in pipeline if o["arrival"] > day]
        stock += deliveries

        demand = max(0, rng.normal(params.mean_demand, params.demand_std))
        demand = float(np.round(demand, 2))

        satisfied = min(stock, demand)
        stock -= satisfied
        unmet = demand - satisfied
        backlog += unmet

        order = 0
        if stock <= params.reorder_point:
            order = params.reorder_qty
            pipeline.append({"qty": params.reorder_qty, "arrival": day + params.lead_time})

        records.append(
            {
                "Hari": day,
                "Stok tersedia": np.round(stock, 2),
                "Kedatangan barang": deliveries,
                "Permintaan": demand,
                "Order ditempatkan": order,
                "Backlog": np.round(backlog, 2),
            }
        )

    return pd.DataFrame(records)


def summarize(df: pd.DataFrame) -> dict:
    served = df["Permintaan"] - df["Backlog"].diff().clip(lower=0).fillna(0)
    fill_rate = served.sum() / df["Permintaan"].sum() if df["Permintaan"].sum() else 1.0
    stockouts = (df["Stok tersedia"] == 0).sum()

    return {
        "Stok awal": df["Stok tersedia"].iloc[0],
        "Stok akhir": df["Stok tersedia"].iloc[-1],
        "Total permintaan": df["Permintaan"].sum(),
        "Tingkat pelayanan": f"{fill_rate * 100:,.2f}%",
        "Jumlah hari stockout": int(stockouts),
        "Backlog akhir": df["Backlog"].iloc[-1],
    }


def scenario_curves(days: int = 360) -> pd.DataFrame:
    day = np.arange(days)
    baseline = 200 + 0.8 * day
    step = 200 + np.where(day < 90, 0.8 * day, 0.8 * 90 + 1.8 * (day - 90))
    ramp = np.piecewise(
        day,
        [day < 60, (day >= 60) & (day < 120), day >= 120],
        [
            lambda x: 200 + 0.8 * x,
            lambda x: 200 + 0.8 * 60 + 2.5 * (x - 60),
            lambda x: 200 + 0.8 * 60 + 2.5 * (120 - 60) + 3.0 * (x - 120),
        ],
    )
    return pd.DataFrame(
        {
            "Hari": day,
            "Baseline (konstan u=1)": baseline,
            "Step (lonjakan hari 90)": step,
            "Ramp (naik bertahap 60-120)": ramp,
        }
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

        df = simulate_inventory(params)
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

