"""锁定日前购电计划并依据实际 SOC 进行因果日内执行。"""

from __future__ import annotations

import numpy as np

from config import (
    ABS_TOL_KWH,
    E_MAX_KWH,
    E_MIN_KWH,
    ETA_CHARGE,
    ETA_DISCHARGE,
    N_INTERVALS,
    P_MAX_KWH,
    REL_TOL,
)
from model_lp import solve_remaining_lp


def _clip_soc(soc: float) -> float:
    return float(min(E_MAX_KWH, max(E_MIN_KWH, soc)))


def dispatch_slot_greedy(residual: float, soc_prev: float) -> tuple[float, float, float, float, float]:
    if residual <= 0:
        surplus = -residual
        charge_cap = min(P_MAX_KWH, max(0.0, (E_MAX_KWH - soc_prev) / ETA_CHARGE))
        charge = min(surplus, charge_cap)
        curtail = surplus - charge
        discharge = 0.0
        emergency = 0.0
    else:
        discharge_cap = min(P_MAX_KWH, max(0.0, ETA_DISCHARGE * (soc_prev - E_MIN_KWH)))
        discharge = min(residual, discharge_cap)
        emergency = residual - discharge
        charge = 0.0
        curtail = 0.0
    soc_next = _clip_soc(soc_prev + ETA_CHARGE * charge - discharge / ETA_DISCHARGE)
    return charge, discharge, emergency, curtail, soc_next


def dispatch_slot_rho(
    residual: float,
    soc_prev: float,
    planned_soc: float,
    rho: float,
) -> tuple[float, float, float, float, float]:
    """在 E_min 与计划 SOC 之间设置保护下界，剩余缺口由紧急购电补足。

    rho=0 时退化为放电至 E_min 的贪心策略；紧急购电不得用于储能充电。
    """
    reserve = E_MIN_KWH + float(rho) * (float(planned_soc) - E_MIN_KWH)
    reserve = min(E_MAX_KWH, max(E_MIN_KWH, reserve))
    if residual <= 0:
        return dispatch_slot_greedy(residual, soc_prev)
    discharge_cap = min(P_MAX_KWH, max(0.0, ETA_DISCHARGE * (soc_prev - reserve)))
    discharge = min(residual, discharge_cap)
    emergency = residual - discharge
    soc_next = _clip_soc(soc_prev - discharge / ETA_DISCHARGE)
    return 0.0, discharge, emergency, 0.0, soc_next


def simulate_day(
    price: np.ndarray,
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    purchase_kwh: np.ndarray,
    soc0: float,
    planned_soc: np.ndarray | None = None,
    rho: float = 0.0,
) -> dict:
    """锁定计划购电量，仅使用当前时段真实数据调度储能。"""
    n = N_INTERVALS
    charge = np.zeros(n)
    discharge = np.zeros(n)
    emergency = np.zeros(n)
    curtail = np.zeros(n)
    soc = np.zeros(n)
    soc_prev = float(soc0)
    if soc_prev < E_MIN_KWH - ABS_TOL_KWH or soc_prev > E_MAX_KWH + ABS_TOL_KWH:
        raise ValueError(f"actual SOC0 {soc_prev} outside [{E_MIN_KWH}, {E_MAX_KWH}]")
    use_rho = float(rho) > 0.0 and planned_soc is not None
    if use_rho and len(planned_soc) != n:
        raise ValueError("planned_soc length must be 144")

    for t in range(n):
        residual = load_kwh[t] - pv_kwh[t] - purchase_kwh[t]
        if use_rho:
            charge[t], discharge[t], emergency[t], curtail[t], soc_prev = dispatch_slot_rho(
                residual, soc_prev, float(planned_soc[t]), float(rho)
            )
        else:
            charge[t], discharge[t], emergency[t], curtail[t], soc_prev = dispatch_slot_greedy(
                residual, soc_prev
            )
        soc[t] = soc_prev

    shortage = load_kwh - pv_kwh - purchase_kwh - discharge + charge + curtail - emergency
    return {
        "charge_kwh": charge,
        "discharge_kwh": discharge,
        "emergency_kwh": emergency,
        "curtail_kwh": curtail,
        "soc_end_kwh": soc,
        "soc0_kwh": float(soc0),
        "soc24_kwh": float(soc[-1]),
        "plan_cost": float(np.dot(price, purchase_kwh)),
        "emergency_cost": float(np.dot(5.0 * price, emergency)),
        "n_emergency_slots": int(np.sum(emergency > ABS_TOL_KWH)),
        "max_unserved_kwh": float(np.max(np.maximum(shortage, 0.0))),
        "dispatch": "rho" if use_rho else "greedy",
        "rho": float(rho) if use_rho else 0.0,
        "mpc_stride": None,
    }


def simulate_day_mpc(
    price: np.ndarray,
    load_actual_kwh: np.ndarray,
    pv_actual_kwh: np.ndarray,
    load_forecast_kwh: np.ndarray,
    pv_forecast_kwh: np.ndarray,
    purchase_kwh: np.ndarray,
    soc0: float,
    soc_mu: float = 0.0,
    stride: int = 1,
) -> dict:
    """锁定购电量 G，重解剩余时域储能线性规划；当前时段使用真实值，后续时段使用预测值。"""
    n = N_INTERVALS
    stride = max(1, int(stride))
    charge = np.zeros(n)
    discharge = np.zeros(n)
    emergency = np.zeros(n)
    curtail = np.zeros(n)
    soc = np.zeros(n)
    soc_prev = float(soc0)
    if soc_prev < E_MIN_KWH - ABS_TOL_KWH or soc_prev > E_MAX_KWH + ABS_TOL_KWH:
        raise ValueError(f"actual SOC0 {soc_prev} outside [{E_MIN_KWH}, {E_MAX_KWH}]")

    plan_c = np.zeros(n)
    plan_d = np.full(n, np.nan)
    plan_origin = -1
    have_plan = False

    for t in range(n):
        if t == 0 or (t - plan_origin) >= stride or not have_plan:
            load_h = load_forecast_kwh[t:].copy()
            pv_h = pv_forecast_kwh[t:].copy()
            load_h[0] = load_actual_kwh[t]
            pv_h[0] = pv_actual_kwh[t]
            try:
                rem = solve_remaining_lp(
                    price[t:],
                    load_h,
                    pv_h,
                    purchase_kwh[t:],
                    soc_prev,
                    soc_mu=soc_mu,
                )
                plan_c[t:] = rem["charge_kwh"]
                plan_d[t:] = rem["discharge_kwh"]
                plan_origin = t
                have_plan = True
            except Exception:
                have_plan = False
                plan_origin = t

        residual = load_actual_kwh[t] - pv_actual_kwh[t] - purchase_kwh[t]
        if residual <= 0:
            charge[t], discharge[t], emergency[t], curtail[t], soc_prev = dispatch_slot_greedy(residual, soc_prev)
        else:
            discharge_cap = min(P_MAX_KWH, max(0.0, ETA_DISCHARGE * (soc_prev - E_MIN_KWH)))
            if have_plan and np.isfinite(plan_d[t]):
                planned = max(0.0, float(plan_d[t]))
            else:
                planned = discharge_cap
            discharge[t] = min(residual, discharge_cap, planned)
            emergency[t] = residual - discharge[t]
            charge[t] = 0.0
            curtail[t] = 0.0
            soc_prev = _clip_soc(soc_prev + ETA_CHARGE * charge[t] - discharge[t] / ETA_DISCHARGE)
        soc[t] = soc_prev

    shortage = load_actual_kwh - pv_actual_kwh - purchase_kwh - discharge + charge + curtail - emergency
    return {
        "charge_kwh": charge,
        "discharge_kwh": discharge,
        "emergency_kwh": emergency,
        "curtail_kwh": curtail,
        "soc_end_kwh": soc,
        "soc0_kwh": float(soc0),
        "soc24_kwh": float(soc[-1]),
        "plan_cost": float(np.dot(price, purchase_kwh)),
        "emergency_cost": float(np.dot(5.0 * price, emergency)),
        "n_emergency_slots": int(np.sum(emergency > ABS_TOL_KWH)),
        "max_unserved_kwh": float(np.max(np.maximum(shortage, 0.0))),
        "dispatch": "mpc",
        "mpc_stride": stride,
    }


def validate_actual(actual: dict, purchase: np.ndarray, load_kwh: np.ndarray, pv_kwh: np.ndarray) -> list[str]:
    errors = []
    tol = lambda scale: max(ABS_TOL_KWH, REL_TOL * abs(scale))
    soc_prev = actual["soc0_kwh"]
    for t in range(N_INTERVALS):
        residual = (
            purchase[t]
            + pv_kwh[t]
            + actual["discharge_kwh"][t]
            + actual["emergency_kwh"][t]
            - load_kwh[t]
            - actual["charge_kwh"][t]
            - actual["curtail_kwh"][t]
        )
        if abs(residual) > tol(max(load_kwh[t], 1.0)):
            errors.append(f"actual t={t} energy residual {residual}")
        soc_expected = soc_prev + ETA_CHARGE * actual["charge_kwh"][t] - actual["discharge_kwh"][t] / ETA_DISCHARGE
        if abs(soc_expected - actual["soc_end_kwh"][t]) > tol(max(actual["soc_end_kwh"][t], 1.0)):
            errors.append(f"actual t={t} SOC mismatch")
        if actual["soc_end_kwh"][t] < E_MIN_KWH - ABS_TOL_KWH or actual["soc_end_kwh"][t] > E_MAX_KWH + ABS_TOL_KWH:
            errors.append(f"actual t={t} SOC out of bounds {actual['soc_end_kwh'][t]}")
        if actual["charge_kwh"][t] > P_MAX_KWH + ABS_TOL_KWH or actual["discharge_kwh"][t] > P_MAX_KWH + ABS_TOL_KWH:
            errors.append(f"actual t={t} power out of bounds")
        if actual["charge_kwh"][t] > ABS_TOL_KWH and actual["discharge_kwh"][t] > ABS_TOL_KWH:
            errors.append(f"actual t={t} simultaneous charge/discharge")
        if actual["emergency_kwh"][t] < -ABS_TOL_KWH:
            errors.append(f"actual t={t} negative emergency")
        soc_prev = actual["soc_end_kwh"][t]
    if actual["max_unserved_kwh"] > ABS_TOL_KWH:
        errors.append(f"unserved energy {actual['max_unserved_kwh']}")
    return errors
