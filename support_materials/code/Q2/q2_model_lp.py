"""日前购电线性规划与剩余时域调度线性规划，充放电量按交流侧计量。"""

from __future__ import annotations

import numpy as np
import pulp
from scipy.optimize import linprog

from config import (
    ABS_TOL_KWH,
    E_MAX_KWH,
    E_MIN_KWH,
    ETA_CHARGE,
    ETA_DISCHARGE,
    N_INTERVALS,
    P_MAX_KWH,
    REL_TOL,
    REMAINING_LP_TIME_LIMIT_S,
    SIMULTANEOUS_TOL,
    SOLVER_TIME_LIMIT_S,
    TERMINAL_LAMBDA,
    TERMINAL_TARGET_KWH,
)


def _val(var) -> float:
    value = pulp.value(var)
    return 0.0 if value is None else float(value)


def solve_day_lp(
    price: np.ndarray,
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    soc0: float,
    terminal_mode: str = "none",
    soc_mu: float = 0.0,
    terminal_soc: float | None = None,
) -> dict:
    n = N_INTERVALS
    if len(price) != n or len(load_kwh) != n or len(pv_kwh) != n:
        raise ValueError("LP input length must be 144")
    if soc0 < E_MIN_KWH - ABS_TOL_KWH or soc0 > E_MAX_KWH + ABS_TOL_KWH:
        raise ValueError(f"planned SOC0 {soc0} outside [{E_MIN_KWH}, {E_MAX_KWH}]")

    prob = pulp.LpProblem("q2_day_ahead", pulp.LpMinimize)
    g = [pulp.LpVariable(f"G_{t}", lowBound=0) for t in range(n)]
    c = [pulp.LpVariable(f"c_{t}", lowBound=0, upBound=P_MAX_KWH) for t in range(n)]
    d = [pulp.LpVariable(f"d_{t}", lowBound=0, upBound=P_MAX_KWH) for t in range(n)]
    w = [pulp.LpVariable(f"w_{t}", lowBound=0) for t in range(n)]
    e = [pulp.LpVariable(f"E_{t}", lowBound=E_MIN_KWH, upBound=E_MAX_KWH) for t in range(n)]

    eps = 1e-7
    obj = pulp.lpSum(price[t] * g[t] + eps * (c[t] + d[t]) for t in range(n))
    if soc_mu:
        obj -= float(soc_mu) * e[n - 1]
    if terminal_soc is not None and terminal_mode != "none":
        raise ValueError("terminal_soc cannot combine with terminal_mode")
    if terminal_mode == "track6000":
        surplus = pulp.LpVariable("term_pos", lowBound=0)
        shortage = pulp.LpVariable("term_neg", lowBound=0)
        obj += TERMINAL_LAMBDA * (surplus + shortage)
    elif terminal_mode != "none":
        raise ValueError(f"unknown terminal_mode {terminal_mode}")
    prob += obj

    for t in range(n):
        prev = soc0 if t == 0 else e[t - 1]
        prob += g[t] + pv_kwh[t] + d[t] == load_kwh[t] + c[t] + w[t]
        prob += e[t] == prev + ETA_CHARGE * c[t] - d[t] / ETA_DISCHARGE
    if terminal_mode == "track6000":
        prob += e[n - 1] - TERMINAL_TARGET_KWH == surplus - shortage
    if terminal_soc is not None:
        target = float(terminal_soc)
        if target < E_MIN_KWH - ABS_TOL_KWH or target > E_MAX_KWH + ABS_TOL_KWH:
            raise ValueError(f"terminal_soc {target} outside [{E_MIN_KWH}, {E_MAX_KWH}]")
        prob += e[n - 1] == target

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=SOLVER_TIME_LIMIT_S))
    status_name = pulp.LpStatus[status]
    if status_name != "Optimal":
        raise RuntimeError(f"Q2 LP not Optimal: {status_name}")

    purchase = np.array([_val(g[t]) for t in range(n)])
    charge = np.array([_val(c[t]) for t in range(n)])
    discharge = np.array([_val(d[t]) for t in range(n)])
    curtail = np.array([_val(w[t]) for t in range(n)])
    soc = np.array([_val(e[t]) for t in range(n)])
    simultaneous = int(np.sum((charge > SIMULTANEOUS_TOL) & (discharge > SIMULTANEOUS_TOL)))
    return {
        "status": status_name,
        "purchase_kwh": purchase,
        "charge_kwh": charge,
        "discharge_kwh": discharge,
        "curtail_kwh": curtail,
        "soc_end_kwh": soc,
        "soc0_kwh": float(soc0),
        "plan_cost": float(np.dot(price, purchase)),
        "n_simultaneous": simultaneous,
        "terminal_mode": terminal_mode if terminal_soc is None else "hard",
        "soc_mu": float(soc_mu),
        "terminal_soc": None if terminal_soc is None else float(terminal_soc),
        "terminal_abs_dev": abs(float(soc[-1]) - (float(terminal_soc) if terminal_soc is not None else TERMINAL_TARGET_KWH)),
    }


def _solve_remaining_highs(
    price: np.ndarray,
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    purchase_kwh: np.ndarray,
    soc0: float,
    soc_mu: float,
) -> dict | None:
    n = len(price)
    nvar = 5 * n
    c_obj = np.zeros(nvar)
    for t in range(n):
        c_obj[t] = 1e-7
        c_obj[n + t] = 1e-7
        c_obj[3 * n + t] = 5.0 * float(price[t])
    c_obj[4 * n + n - 1] -= float(soc_mu)

    bounds = [(0.0, P_MAX_KWH)] * n + [(0.0, P_MAX_KWH)] * n
    bounds += [(0.0, None)] * n + [(0.0, None)] * n
    bounds += [(E_MIN_KWH, E_MAX_KWH)] * n

    a_eq = np.zeros((2 * n, nvar))
    b_eq = np.zeros(2 * n)
    for t in range(n):
        a_eq[t, t] = -1.0
        a_eq[t, n + t] = 1.0
        a_eq[t, 2 * n + t] = -1.0
        a_eq[t, 3 * n + t] = 1.0
        b_eq[t] = float(load_kwh[t] - pv_kwh[t] - purchase_kwh[t])
        a_eq[n + t, 4 * n + t] = 1.0
        a_eq[n + t, t] = -ETA_CHARGE
        a_eq[n + t, n + t] = 1.0 / ETA_DISCHARGE
        if t == 0:
            b_eq[n + t] = float(soc0)
        else:
            a_eq[n + t, 4 * n + t - 1] = -1.0

    result = linprog(c_obj, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not result.success or result.x is None:
        return None
    x = result.x
    charge = np.maximum(x[0:n], 0.0)
    discharge = np.maximum(x[n : 2 * n], 0.0)
    curtail = np.maximum(x[2 * n : 3 * n], 0.0)
    emergency = np.maximum(x[3 * n : 4 * n], 0.0)
    soc = x[4 * n : 5 * n]
    return {
        "status": "Optimal",
        "charge_kwh": charge,
        "discharge_kwh": discharge,
        "curtail_kwh": curtail,
        "emergency_kwh": emergency,
        "soc_end_kwh": soc,
        "solver": "highs",
    }


def _solve_remaining_pulp(
    price: np.ndarray,
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    purchase_kwh: np.ndarray,
    soc0: float,
    soc_mu: float,
) -> dict:
    n = len(price)
    prob = pulp.LpProblem("q2_remaining", pulp.LpMinimize)
    c = [pulp.LpVariable(f"c_{t}", lowBound=0, upBound=P_MAX_KWH) for t in range(n)]
    d = [pulp.LpVariable(f"d_{t}", lowBound=0, upBound=P_MAX_KWH) for t in range(n)]
    w = [pulp.LpVariable(f"w_{t}", lowBound=0) for t in range(n)]
    gem = [pulp.LpVariable(f"gem_{t}", lowBound=0) for t in range(n)]
    e = [pulp.LpVariable(f"E_{t}", lowBound=E_MIN_KWH, upBound=E_MAX_KWH) for t in range(n)]
    eps = 1e-7
    obj = pulp.lpSum(5.0 * price[t] * gem[t] + eps * (c[t] + d[t]) for t in range(n))
    if soc_mu:
        obj -= float(soc_mu) * e[n - 1]
    prob += obj
    for t in range(n):
        prev = soc0 if t == 0 else e[t - 1]
        prob += purchase_kwh[t] + pv_kwh[t] + d[t] + gem[t] == load_kwh[t] + c[t] + w[t]
        prob += e[t] == prev + ETA_CHARGE * c[t] - d[t] / ETA_DISCHARGE
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=REMAINING_LP_TIME_LIMIT_S))
    status_name = pulp.LpStatus[status]
    if status_name != "Optimal":
        raise RuntimeError(f"Q2 remaining LP not Optimal: {status_name}")
    return {
        "status": status_name,
        "charge_kwh": np.array([_val(c[t]) for t in range(n)]),
        "discharge_kwh": np.array([_val(d[t]) for t in range(n)]),
        "curtail_kwh": np.array([_val(w[t]) for t in range(n)]),
        "emergency_kwh": np.array([_val(gem[t]) for t in range(n)]),
        "soc_end_kwh": np.array([_val(e[t]) for t in range(n)]),
        "solver": "cbc",
    }


def solve_remaining_lp(
    price: np.ndarray,
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    purchase_kwh: np.ndarray,
    soc0: float,
    soc_mu: float = 0.0,
) -> dict:
    n = len(price)
    if not (len(load_kwh) == n and len(pv_kwh) == n and len(purchase_kwh) == n):
        raise ValueError("remaining LP arrays must share length")
    soc0 = float(min(E_MAX_KWH, max(E_MIN_KWH, soc0)))
    highs = _solve_remaining_highs(price, load_kwh, pv_kwh, purchase_kwh, soc0, soc_mu)
    if highs is not None:
        return highs
    return _solve_remaining_pulp(price, load_kwh, pv_kwh, purchase_kwh, soc0, soc_mu)


def _tol(scale: float) -> float:
    return max(ABS_TOL_KWH, REL_TOL * abs(scale))


def validate_plan(plan: dict, price: np.ndarray, load_kwh: np.ndarray, pv_kwh: np.ndarray) -> list[str]:
    errors = []
    soc_prev = plan["soc0_kwh"]
    for t in range(N_INTERVALS):
        residual = (
            plan["purchase_kwh"][t]
            + pv_kwh[t]
            + plan["discharge_kwh"][t]
            - load_kwh[t]
            - plan["charge_kwh"][t]
            - plan["curtail_kwh"][t]
        )
        if abs(residual) > _tol(max(load_kwh[t], 1.0)):
            errors.append(f"plan t={t} energy residual {residual}")
        soc_expected = soc_prev + ETA_CHARGE * plan["charge_kwh"][t] - plan["discharge_kwh"][t] / ETA_DISCHARGE
        if abs(soc_expected - plan["soc_end_kwh"][t]) > _tol(max(plan["soc_end_kwh"][t], 1.0)):
            errors.append(f"plan t={t} SOC mismatch")
        if plan["soc_end_kwh"][t] < E_MIN_KWH - ABS_TOL_KWH or plan["soc_end_kwh"][t] > E_MAX_KWH + ABS_TOL_KWH:
            errors.append(f"plan t={t} SOC out of bounds")
        if plan["charge_kwh"][t] > P_MAX_KWH + ABS_TOL_KWH or plan["discharge_kwh"][t] > P_MAX_KWH + ABS_TOL_KWH:
            errors.append(f"plan t={t} power out of bounds")
        soc_prev = plan["soc_end_kwh"][t]
    return errors
