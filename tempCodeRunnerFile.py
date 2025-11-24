"""Fungsi inti simulasi stok untuk sistem dinamik inventori minimarket."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
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


def simulate_inventory(
    days: int,
    initial_stock: int,
    reorder_point: int,
    reorder_qty: int,
    mean_demand: float,
    demand_std: float,
    lead_time: int,
    seed: int,
) -> pd.DataFrame:
    """Model stok barang sederhana dengan kebijakan reorder point."""
    rng = np.random.default_rng(seed)
    stock = initial_stock
    backlog = 0.0
    pipeline: List[dict[str, int]] = []
    records = []

    for day in range(days + 1):
        deliveries = sum(o["qty"] for o in pipeline if o["arrival"] == day)
        pipeline = [o for o in pipeline if o["arrival"] > day]
        stock += deliveries

        demand = max(0, rng.normal(mean_demand, demand_std))
        demand = float(np.round(demand, 2))

        satisfied = min(stock, demand)
        stock -= satisfied
        unmet = demand - satisfied
        backlog += unmet

        order = 0
        if stock <= reorder_point:
            order = reorder_qty
            pipeline.append({"qty": reorder_qty, "arrival": day + lead_time})

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

    df = pd.DataFrame(records)
    return df


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
    df = pd.DataFrame(
        {
            "Hari": day,
            "Baseline (konstan u=1)": baseline,
            "Step (lonjakan hari 90)": step,
            "Ramp (naik bertahap 60-120)": ramp,
        }
    )
    return df

