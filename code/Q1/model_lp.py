"""问题一计划购电的确定性线性规划。"""

from __future__ import annotations

import pulp
import numpy as np
import pandas as pd

from config import (
    E0_KWH,
    E_MAX_KWH,
    E_MIN_KWH,
    ETA,
    P_MAX_CHARGE_BATT_KWH,
    P_MAX_DISCHARGE_BATT_KWH,
    P_MAX_KWH,
    SOLVER_TIME_LIMIT_S,
)


def solve_lp(frame: pd.DataFrame) -> dict:
    n = len(frame)
    price = frame["price"].to_numpy()
    load = frame["load_kwh"].to_numpy()
    pv = frame["pv_kwh"].to_numpy()

    prob = pulp.LpProblem("q1_planned_purchase", pulp.LpMinimize)
    G = [pulp.LpVariable(f"G_{t}", lowBound=0) for t in range(n)]
    c = [pulp.LpVariable(f"c_{t}", lowBound=0, upBound=P_MAX_CHARGE_BATT_KWH) for t in range(n)]
    d = [pulp.LpVariable(f"d_{t}", lowBound=0, upBound=P_MAX_DISCHARGE_BATT_KWH) for t in range(n)]
    w = [pulp.LpVariable(f"w_{t}", lowBound=0) for t in range(n)]
    E = [pulp.LpVariable(f"E_{t}", lowBound=E_MIN_KWH, upBound=E_MAX_KWH) for t in range(n)]

    prob += pulp.lpSum(price[t] * G[t] for t in range(n))

    for t in range(n):
        prev = E0_KWH if t == 0 else E[t - 1]
        prob += E[t] == prev + c[t] - d[t]
        prob += G[t] + pv[t] + ETA * d[t] == load[t] + c[t] / ETA + w[t]
        # 接口功率约束：交流侧充电 c/η 和交流侧放电 ηd 均不得超过 5000 kW。
        prob += c[t] / ETA <= P_MAX_KWH
        prob += ETA * d[t] <= P_MAX_KWH
    prob += E[n - 1] == E0_KWH

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=SOLVER_TIME_LIMIT_S))
    status_name = pulp.LpStatus[status]
    if status_name != "Optimal":
        raise RuntimeError(f"Q1 LP did not reach Optimal, status={status_name}")

    result = {
        "status": status_name,
        "objective": float(pulp.value(prob.objective)),
        "purchase_kwh": np.array([float(pulp.value(G[t])) for t in range(n)]),
        "charge_kwh": np.array([float(pulp.value(c[t])) for t in range(n)]),
        "discharge_kwh": np.array([float(pulp.value(d[t])) for t in range(n)]),
        "curtail_kwh": np.array([float(pulp.value(w[t])) for t in range(n)]),
        "soc_end_kwh": np.array([float(pulp.value(E[t])) for t in range(n)]),
        "solver": "PULP_CBC_CMD",
    }
    return result
