"""与各光伏预报发布时刻对齐的因果净负荷残差分位数。

残差定义为真实值减点预测值，符号约定与问题二一致。负荷按分位数 q 修正，
光伏按分位数 1-q 修正。偏移量仅使用严格早于决策日的数据；48 小时尾段
还要求相应次日真实数据已经闭合。本模块仅通过滚动策略中的受控分支进入
正式计算路径。
"""

from __future__ import annotations

import numpy as np

from config import DT_HOURS, ISSUE_HOURS, LOCK_SLOTS, N_INTERVALS, SIGMA_MIN_SAMPLES
from load_forecast import horizon_load_kw, tomorrow_forecast_kw
from pv_forecast import aligned_actual_pv, tomorrow_pv_kw


def q_lock_at(q_lock, hour: int) -> float:
    """返回单个发布时刻对应的锁定段分位数；四元组依次对应 0、6、12、18 时。"""
    if isinstance(q_lock, (list, tuple, np.ndarray)):
        if len(q_lock) != len(ISSUE_HOURS):
            raise ValueError("q_lock sequence must have one value per issue hour")
        return float(q_lock[ISSUE_HOURS.index(hour)])
    return float(q_lock)


def q_vector(
    n_horizon: int,
    n_today: int,
    q_lock: float,
    q_open: float,
    q_evening: float,
    lock_slots: int = LOCK_SLOTS,
) -> np.ndarray:
    q = np.empty(n_horizon, dtype=float)
    lock_n = min(int(lock_slots), n_today, n_horizon)
    q[:lock_n] = q_lock
    open_end = min(n_today, n_horizon)
    q[lock_n:open_end] = q_open
    if n_horizon > n_today:
        q[n_today:] = q_evening
    return q


def slot_quantile(stacked: np.ndarray, q, min_samples: int = SIGMA_MIN_SAMPLES) -> np.ndarray:
    stacked = np.asarray(stacked, dtype=float)
    if stacked.size == 0:
        n_slots = len(q) if not np.isscalar(q) else 0
        return np.zeros(n_slots)
    n_slots = stacked.shape[1]
    q_arr = np.full(n_slots, float(q)) if np.isscalar(q) else np.asarray(q, dtype=float)
    out = np.zeros(n_slots)
    for s in range(n_slots):
        col = stacked[:, s]
        col = col[~np.isnan(col)]
        if col.size < min_samples:
            out[s] = 0.0
        else:
            out[s] = float(np.quantile(col, float(q_arr[s])))
    return out


def apply_net_quantile(
    load_kw: np.ndarray,
    pv_kw: np.ndarray,
    load_off: np.ndarray,
    pv_off: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.maximum(np.asarray(load_kw, dtype=float) + load_off, 0.0),
        np.maximum(np.asarray(pv_kw, dtype=float) + pv_off, 0.0),
    )


def _aligned_actual_load(actual_kw: np.ndarray) -> np.ndarray:
    n_days = actual_kw.shape[0]
    aligned = np.full((n_days, len(ISSUE_HOURS), N_INTERVALS), np.nan)
    for i, hour in enumerate(ISSUE_HOURS):
        start = hour * 6
        for d in range(n_days):
            for step in range(N_INTERVALS):
                slot = start + step
                if slot < N_INTERVALS:
                    aligned[d, i, step] = actual_kw[d, slot]
                elif d + 1 < n_days:
                    aligned[d, i, step] = actual_kw[d + 1, slot - N_INTERVALS]
    return aligned


def _load_point_24(load_kw: np.ndarray, dates, typical: np.ndarray, upside_nowcast: bool = False) -> np.ndarray:
    n_days = load_kw.shape[0]
    out = np.zeros((n_days, len(ISSUE_HOURS), N_INTERVALS))
    for d in range(n_days):
        actual_today = load_kw[d]
        for i, hour in enumerate(ISSUE_HOURS):
            start = hour * 6
            out[d, i] = horizon_load_kw(
                load_kw,
                dates,
                typical,
                d,
                start,
                N_INTERVALS,
                actual_today if hour > 0 else None,
                upside_nowcast=upside_nowcast,
            )
    return out


def _tail_from_start(values: np.ndarray, start_slot: int, n_slots: int = N_INTERVALS) -> np.ndarray:
    extra = np.full(n_slots, np.nan)
    piece = np.asarray(values[start_slot:], dtype=float)
    extra[: piece.size] = piece
    return extra


class QuantileBank:
    """按发布时刻组织残差数据立方体；offsets(day, ...) 仅使用已经闭合的历史数据。"""

    def __init__(
        self,
        load_resid24: np.ndarray,
        pv_resid24: np.ndarray,
        load_resid_extra: np.ndarray,
        pv_resid_extra: np.ndarray,
    ):
        self.load_resid24 = load_resid24
        self.pv_resid24 = pv_resid24
        self.load_resid_extra = load_resid_extra
        self.pv_resid_extra = pv_resid_extra

    @classmethod
    def build(cls, bundle: dict, upside_nowcast: bool = False) -> "QuantileBank":
        load_kw = np.asarray(bundle["year"]["load_kwh"], dtype=float) / DT_HOURS
        dates = bundle["year"]["dates"]
        typical = bundle["prices"]["typical_load_kw"].to_numpy(dtype=float)
        interp = np.asarray(bundle["interp"], dtype=float)
        pv_actual = np.asarray(bundle["year"]["pv_kw"], dtype=float)
        n_days = load_kw.shape[0]

        load_hat = _load_point_24(load_kw, dates, typical, upside_nowcast=upside_nowcast)
        load_act = _aligned_actual_load(load_kw)
        pv_act = aligned_actual_pv(pv_actual, interp)
        load_resid24 = load_act - load_hat
        pv_resid24 = pv_act - interp

        load_resid_extra = np.full((n_days, len(ISSUE_HOURS), N_INTERVALS), np.nan)
        pv_resid_extra = np.full_like(load_resid_extra, np.nan)
        for d in range(n_days):
            tom_load = tomorrow_forecast_kw(load_kw, dates, typical, d)
            for i, hour in enumerate(ISSUE_HOURS):
                start = hour * 6
                hat = _tail_from_start(tom_load, start)
                hat_pv = _tail_from_start(tomorrow_pv_kw(pv_actual, d), start)
                if d + 1 < n_days:
                    act_load = _tail_from_start(load_kw[d + 1], start)
                    act_pv = _tail_from_start(pv_actual[d + 1], start)
                    load_resid_extra[d, i] = act_load - hat
                    pv_resid_extra[d, i] = act_pv - hat_pv
                else:
                    load_resid_extra[d, i] = np.nan
        return cls(load_resid24, pv_resid24, load_resid_extra, pv_resid_extra)

    def offsets(
        self,
        day: int,
        iss: int,
        n_horizon: int,
        q_vec: np.ndarray,
        window: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        q_vec = np.asarray(q_vec, dtype=float)
        if q_vec.size != n_horizon:
            raise ValueError("q_vec length must equal n_horizon")
        load_off = np.zeros(n_horizon)
        pv_off = np.zeros(n_horizon)
        n24 = min(n_horizon, N_INTERVALS)
        start = 0 if window is None else max(0, day - int(window))
        if day > start:
            load_off[:n24] = slot_quantile(self.load_resid24[start:day, iss, :n24], q_vec[:n24])
            pv_off[:n24] = slot_quantile(self.pv_resid24[start:day, iss, :n24], 1.0 - q_vec[:n24])
        extra_n = n_horizon - n24
        extra_end = max(0, day - 1)
        extra_start = 0 if window is None else max(0, extra_end - int(window))
        if extra_n > 0 and extra_end > extra_start:
            load_off[n24:] = slot_quantile(
                self.load_resid_extra[extra_start:extra_end, iss, :extra_n], q_vec[n24:]
            )
            pv_off[n24:] = slot_quantile(
                self.pv_resid_extra[extra_start:extra_end, iss, :extra_n], 1.0 - q_vec[n24:]
            )
        return load_off, pv_off
