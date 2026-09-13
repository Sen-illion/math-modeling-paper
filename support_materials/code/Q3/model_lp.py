"""含偏差电价、虚拟紧急购电和终端 SOC 的滚动购电线性规划。"""

from __future__ import annotations

import numpy as np
import pulp

from config import (
    ABS_TOL_KWH,
    E_MAX_KWH,
    E_MIN_KWH,
    E_REF_KWH,
    ETA_CHARGE,
    ETA_DISCHARGE,
    P_MAX_KWH,
    SOLVER_TIME_LIMIT_S,
    TERMINAL_LAMBDA,
)


def solve_rolling_lp(
    price: np.ndarray,
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    soc0: float,
    n_today: int,
    g_plan_today: np.ndarray | None = None,
    lock_to_plan: bool = False,
    terminal_lambda: float = TERMINAL_LAMBDA,
    e_ref: float = E_REF_KWH,
    add_only: bool = False,
    hard_terminal: bool = False,
) -> dict:
    n = len(price)
    if not (len(load_kwh) == n and len(pv_kwh) == n):
        raise ValueError("LP arrays must share the same horizon length")
    if n_today < 1 or n_today > n:
        raise ValueError("n_today must lie in the horizon")
    if soc0 < E_MIN_KWH - ABS_TOL_KWH or soc0 > E_MAX_KWH + ABS_TOL_KWH:
        raise ValueError(f"SOC0 {soc0} outside [{E_MIN_KWH}, {E_MAX_KWH}]")

    prob = pulp.LpProblem("q3_rolling", pulp.LpMinimize)
    g = [pulp.LpVariable(f"G_{t}", lowBound=0) for t in range(n)]
    c = [pulp.LpVariable(f"c_{t}", lowBound=0, upBound=P_MAX_KWH) for t in range(n)]
    d = [pulp.LpVariable(f"d_{t}", lowBound=0, upBound=P_MAX_KWH) for t in range(n)]
    w = [pulp.LpVariable(f"w_{t}", lowBound=0) for t in range(n)]
    gem = [pulp.LpVariable(f"Gem_{t}", lowBound=0) for t in range(n)]
    e = [pulp.LpVariable(f"E_{t}", lowBound=E_MIN_KWH, upBound=E_MAX_KWH) for t in range(n)]
    u = pulp.LpVariable("term_pos", lowBound=0)
    v = pulp.LpVariable("term_neg", lowBound=0)

    eps = 1e-7
    obj = 0 if hard_terminal else terminal_lambda * (u + v)
    for t in range(n):
        obj += 5.0 * price[t] * gem[t] + eps * (c[t] + d[t])
        if t >= n_today:
            obj += price[t] * g[t]

    if g_plan_today is None:
        for t in range(n_today):
            obj += price[t] * g[t]
    else:
        if len(g_plan_today) != n_today:
            raise ValueError("g_plan_today length must equal n_today")
        for t in range(n_today):
            obj += price[t] * float(g_plan_today[t])
            if lock_to_plan:
                prob += g[t] == float(g_plan_today[t])
            elif add_only:
                dp = pulp.LpVariable(f"dp_{t}", lowBound=0)
                obj += 1.5 * price[t] * dp
                prob += g[t] == float(g_plan_today[t]) + dp
            else:
                dp = pulp.LpVariable(f"dp_{t}", lowBound=0)
                dm = pulp.LpVariable(f"dm_{t}", lowBound=0)
                obj += -0.5 * price[t] * dm + 1.5 * price[t] * dp
                prob += g[t] == float(g_plan_today[t]) + dp - dm

    prob += obj

    for t in range(n):
        prev = soc0 if t == 0 else e[t - 1]
        prob += g[t] + pv_kwh[t] + d[t] + gem[t] == load_kwh[t] + c[t] + w[t]
        prob += e[t] == prev + ETA_CHARGE * c[t] - d[t] / ETA_DISCHARGE
    if hard_terminal:
        prob += e[n_today - 1] == float(e_ref)
    else:
        prob += e[n_today - 1] - e_ref == u - v

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=SOLVER_TIME_LIMIT_S))
    status_name = pulp.LpStatus[status]
    if status_name != "Optimal":
        raise RuntimeError(f"Q3 LP not Optimal: {status_name}")

    def _val(var) -> float:
        value = pulp.value(var)
        return 0.0 if value is None else float(value)

    purchase = np.array([_val(g[t]) for t in range(n)])
    return {
        "status": status_name,
        "purchase_kwh": purchase,
        "charge_kwh": np.array([_val(c[t]) for t in range(n)]),
        "discharge_kwh": np.array([_val(d[t]) for t in range(n)]),
        "curtail_kwh": np.array([_val(w[t]) for t in range(n)]),
        "virtual_emergency_kwh": np.array([_val(gem[t]) for t in range(n)]),
        "soc_end_kwh": np.array([_val(e[t]) for t in range(n)]),
        "objective": float(pulp.value(prob.objective)),
        "today_purchase_kwh": purchase[:n_today].copy(),
    }
